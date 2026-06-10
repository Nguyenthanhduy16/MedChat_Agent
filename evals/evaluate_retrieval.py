from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable


def configure_transformer_runtime() -> None:
    os.environ.setdefault("USE_TF", "0")
    os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")


configure_transformer_runtime()

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Fusion, FusionQuery, Prefetch

from backend.api.schemas import ChatRequest, RetrievalOptions
from core.agent import route_question
from core.chat_service import _build_hybrid_query, _enrich_decision_entities
from core.config import get_settings
from core.entity_resolver import resolve_entities
from core.llm import FlagEmbeddingRerankerModel, SentenceTransformerEmbeddingModel
from core.models import EvidenceItem, RetrievalPlan
from core.query_planner import plan_query_facets, retrieval_plan_for_facet
from core.retrieval import _build_query_filter, _query_terms, rerank_evidence
from core.sparse_vectors import build_sparse_vector
from core.text import accent_fold
from core.input_normalizer import normalize_input


DEFAULT_PRECISION_KS = (3, 5, 7)
DEFAULT_RECALL_KS = (5, 7, 9, 11)

FIELD_ALIASES = {
    "careful": {"careful", "than_trong", "warning", "canh_bao"},
    "contraindication": {"contraindication", "chong_chi_dinh"},
    "dosage": {"dosage", "lieu_dung", "lieu_luong_va_cach_dung", "cach_dung"},
    "indication": {"indication", "chi_dinh", "cong_dung"},
    "interaction": {"interaction", "tuong_tac_thuoc"},
    "adverse_effect": {"adverse_effect"},
    "overdose": {"overdose", "xu_tri_qua_lieu", "qua_lieu_va_xu_tri"},
    "describe": {"describe", "overview"},
    "symptoms": {"symptoms"},
    "treatment": {"treatment", "treatment_options", "prevention"},
    "diagnosis": {"diagnosis", "diagnosis_methods"},
}


@dataclass
class RetrievedCandidate:
    path: str
    text: str
    title: str
    field: str | None = None
    score: float = 0.0
    source: str = "unknown"
    trust_tier: str = "local_curated"
    metadata: dict[str, Any] = dataclass_field(default_factory=dict)


@dataclass(frozen=True)
class DenseRunConfig:
    model: str
    collection: str
    label: str


def ensure_project_runtime(executable: str | None = None, project_root: str | None = None) -> str | None:
    exe_path = Path(executable or sys.executable).resolve()
    root_path = Path(project_root or Path(__file__).resolve().parents[1]).resolve()
    expected_venv = root_path / ".venv"
    try:
        exe_path.relative_to(expected_venv)
        return None
    except ValueError:
        return (
            "This evaluation loads local embedding/reranker models and must run inside the project virtual environment.\n"
            f"Current Python: {exe_path}\n\n"
            "Run:\n"
            r"  .\.venv\Scripts\Activate.ps1" + "\n"
            r"  .\.venv\Scripts\python.exe -m evals.evaluate_retrieval --candidate-k 30" + "\n"
        )


def render_progress_bar(label: str, current: int, total: int, width: int = 30) -> str:
    safe_total = max(total, 1)
    safe_current = min(max(current, 0), safe_total)
    ratio = safe_current / safe_total
    filled = int(width * ratio)
    bar = "#" * filled + "-" * (width - filled)
    return f"{label} [{bar}] {safe_current}/{total} {ratio * 100:.1f}%"


class ProgressBar:
    def __init__(self, label: str, total: int, enabled: bool = True, width: int = 30) -> None:
        self.label = label
        self.total = total
        self.enabled = enabled and total > 0
        self.width = width
        self.last_length = 0

    def update(self, current: int) -> None:
        if not self.enabled:
            return
        line = render_progress_bar(self.label, current, self.total, self.width)
        padding = " " * max(self.last_length - len(line), 0)
        print("\r" + line + padding, end="", flush=True)
        self.last_length = len(line)

    def close(self) -> None:
        if self.enabled:
            print()


def normalize_path(value: str | None) -> str:
    return str(value or "").replace("\\", "/")


def sample_user_input(sample: dict[str, Any]) -> str:
    if isinstance(sample.get("user_input"), str):
        return sample["user_input"]
    input_block = sample.get("input")
    if isinstance(input_block, dict) and isinstance(input_block.get("user_input"), str):
        return input_block["user_input"]
    raise ValueError(f"Unsupported evaluation sample schema; missing user_input keys={sorted(sample.keys())}")


def compute_ranking_metrics(
    candidates: list[RetrievedCandidate],
    expected_paths: set[str],
    precision_ks: Iterable[int] = DEFAULT_PRECISION_KS,
    recall_ks: Iterable[int] = DEFAULT_RECALL_KS,
) -> dict[str, float]:
    expected = {normalize_path(path) for path in expected_paths if path}
    metrics: dict[str, float] = {}
    if not expected:
        for k in precision_ks:
            metrics[f"precision@{k}"] = 0.0
        for k in recall_ks:
            metrics[f"recall@{k}"] = 0.0
        metrics["mrr"] = 0.0
        return metrics

    relevant_flags = [normalize_path(candidate.path) in expected for candidate in candidates]
    for k in precision_ks:
        metrics[f"precision@{k}"] = sum(relevant_flags[:k]) / k

    for k in recall_ks:
        retrieved_expected_paths = {
            normalize_path(candidate.path)
            for candidate in candidates[:k]
            if normalize_path(candidate.path) in expected
        }
        metrics[f"recall@{k}"] = len(retrieved_expected_paths) / len(expected)

    reciprocal_rank = 0.0
    for index, is_relevant in enumerate(relevant_flags, start=1):
        if is_relevant:
            reciprocal_rank = 1.0 / index
            break
    metrics["mrr"] = reciprocal_rank
    return metrics


def compute_reference_metrics(
    candidates: list[RetrievedCandidate],
    expected_references: set[str],
    precision_ks: Iterable[int] = DEFAULT_PRECISION_KS,
    recall_ks: Iterable[int] = DEFAULT_RECALL_KS,
) -> dict[str, float]:
    expected = {normalize_path(reference) for reference in expected_references if reference}
    metrics: dict[str, float] = {}
    if not expected:
        for k in precision_ks:
            metrics[f"precision@{k}"] = 0.0
        for k in recall_ks:
            metrics[f"recall@{k}"] = 0.0
        metrics["mrr"] = 0.0
        return metrics

    candidate_keys = [candidate_reference_keys(candidate) for candidate in candidates]
    relevant_flags = [bool(keys & expected) for keys in candidate_keys]
    for k in precision_ks:
        metrics[f"precision@{k}"] = sum(relevant_flags[:k]) / k

    for k in recall_ks:
        retrieved_expected = set()
        for keys in candidate_keys[:k]:
            retrieved_expected.update(keys & expected)
        metrics[f"recall@{k}"] = len(retrieved_expected) / len(expected)

    reciprocal_rank = 0.0
    for index, is_relevant in enumerate(relevant_flags, start=1):
        if is_relevant:
            reciprocal_rank = 1.0 / index
            break
    metrics["mrr"] = reciprocal_rank
    return metrics


def candidate_reference_keys(candidate: RetrievedCandidate) -> set[str]:
    keys = {normalize_path(candidate.path)}
    metadata = candidate.metadata
    for value in (
        metadata.get("path"),
        metadata.get("local_path"),
        metadata.get("id"),
        metadata.get("content_hash"),
    ):
        if value:
            keys.add(normalize_path(str(value)))

    path = normalize_path(str(metadata.get("path") or metadata.get("local_path") or candidate.path))
    slug = Path(path).stem if path else ""
    field_name = str(metadata.get("field") or candidate.field or "")
    chunk_index = metadata.get("chunk_index")
    if slug and field_name and chunk_index is not None:
        for entity_type in ("drug", "condition", "supplement", "ingredient"):
            keys.add(f"{entity_type}:{slug}:{field_name}:{chunk_index}")
        type_slug = str(metadata.get("type_slug") or metadata.get("type") or "").strip()
        if type_slug:
            keys.add(f"{type_slug}:{slug}:{field_name}:{chunk_index}")
    return {key for key in keys if key}


def sample_metadata(sample: dict[str, Any]) -> dict[str, Any]:
    rubric = sample.get("rubric")
    if isinstance(rubric, dict):
        return {
            "case_id": rubric["case_id"],
            "suite": rubric["suite"],
            "category": rubric.get("category"),
            "source_fields": rubric.get("source_fields", []),
            "entities": rubric.get("entities") or rubric.get("expected_entities") or [],
            "expected_references": rubric.get("source_files", []),
        }

    expected_retrieval = sample.get("expected_retrieval")
    if isinstance(expected_retrieval, dict):
        input_block = sample.get("input") if isinstance(sample.get("input"), dict) else {}
        input_entities = input_block.get("entities", [])
        entity_names = []
        if isinstance(input_entities, list):
            for entity in input_entities:
                if isinstance(entity, dict) and entity.get("name"):
                    entity_names.append(str(entity["name"]))
                elif isinstance(entity, str):
                    entity_names.append(entity)
        return {
            "case_id": sample["case_id"],
            "suite": sample["suite"],
            "category": sample.get("category") or sample.get("question_type"),
            "source_fields": expected_retrieval.get("allowed_fields", []),
            "entities": expected_retrieval.get("allowed_entity_names") or entity_names,
            "expected_references": (
                expected_retrieval.get("should_retrieve")
                or expected_retrieval.get("must_retrieve_any")
                or []
            ),
        }

    raise ValueError(f"Unsupported evaluation sample schema; keys={sorted(sample.keys())}")


def aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "overall": _aggregate_group(rows),
        "by_suite": {
            suite: _aggregate_group(items)
            for suite, items in sorted(_group_by(rows, "suite").items())
        },
    }


def _aggregate_group(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    if not rows:
        return {}
    result_names = sorted(
        {
            key
            for row in rows
            for key, value in row.items()
            if isinstance(value, dict) and _looks_like_metric_dict(value)
        }
    )
    aggregated: dict[str, dict[str, float]] = {}
    for result_name in result_names:
        metric_names = sorted(
            {
                metric_name
                for row in rows
                for metric_name, value in row.get(result_name, {}).items()
                if isinstance(value, int | float)
            },
            key=_metric_sort_key,
        )
        aggregated[result_name] = {
            metric_name: mean(
                float(row[result_name][metric_name])
                for row in rows
                if result_name in row and metric_name in row[result_name]
            )
            for metric_name in metric_names
        }
    return aggregated


def _looks_like_metric_dict(value: dict[str, Any]) -> bool:
    return any(
        key == "mrr" or key.startswith("precision@") or key.startswith("recall@")
        for key in value
    )


def _metric_sort_key(name: str) -> tuple[int, int, str]:
    if name == "mrr":
        return (2, 0, name)
    match = re.match(r"(precision|recall)@(\d+)$", name)
    if match:
        group = 0 if match.group(1) == "precision" else 1
        return (group, int(match.group(2)), name)
    return (3, 0, name)


def _group_by(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key, ""))].append(row)
    return dict(grouped)


def diagnostic_metrics(sample: dict[str, Any], candidates: list[RetrievedCandidate], k: int) -> dict[str, Any]:
    top_k = candidates[:k]
    expected_fields = _expected_fields(sample)
    got_fields = {candidate.field or "" for candidate in top_k}
    entities = sample_metadata(sample)["entities"]
    combined_text = " ".join(f"{candidate.title} {candidate.text}" for candidate in top_k)
    entity_hits = sum(
        1
        for entity in entities
        if accent_fold(str(entity)) and accent_fold(str(entity)) in accent_fold(combined_text)
    )
    return {
        f"field_hit@{k}": bool(expected_fields & got_fields) if expected_fields else False,
        f"entity_hit_rate@{k}": entity_hits / max(1, len(entities)),
        f"context_overlap@{k}": max_context_overlap(top_k, sample.get("reference_contexts", [])),
        "retrieved_count": len(candidates),
    }


def max_context_overlap(candidates: list[RetrievedCandidate], reference_contexts: list[Any]) -> float:
    reference_sets = [_token_set(_context_text(context)) for context in reference_contexts if context]
    best = 0.0
    for candidate in candidates:
        candidate_tokens = _token_set(candidate.text)
        if not candidate_tokens:
            continue
        for reference_tokens in reference_sets:
            if reference_tokens:
                best = max(best, len(candidate_tokens & reference_tokens) / len(reference_tokens))
    return best


def _context_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "content", "context", "snippet"):
            if isinstance(value.get(key), str):
                return value[key]
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _token_set(value: str) -> set[str]:
    return {token for token in accent_fold(value).split() if len(token) >= 3}


def _expected_fields(sample: dict[str, Any]) -> set[str]:
    fields: set[str] = set()
    for field_name in sample_metadata(sample)["source_fields"]:
        fields.update(FIELD_ALIASES.get(field_name, {field_name}))
    return fields


def load_dataset(path: Path, suites: set[str] | None, limit: int | None, per_suite: int | None) -> list[dict[str, Any]]:
    samples = json.loads(path.read_text(encoding="utf-8"))
    if suites:
        samples = [sample for sample in samples if sample["rubric"].get("suite") in suites]
    if per_suite is not None:
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for sample in samples:
            suite = str(sample["rubric"].get("suite", ""))
            if len(buckets[suite]) < per_suite:
                buckets[suite].append(sample)
        samples = [sample for suite in sorted(buckets) for sample in buckets[suite]]
    if limit is not None:
        samples = samples[:limit]
    return samples


def parse_dense_configs(values: list[str] | None, default_model: str, default_collection: str) -> list[DenseRunConfig]:
    if not values:
        return [DenseRunConfig(model=default_model, collection=default_collection, label=f"{default_model}@{default_collection}")]

    configs = []
    for value in values:
        if "=" not in value:
            raise ValueError("--dense-collection must use MODEL=COLLECTION")
        model, collection = value.split("=", 1)
        model = model.strip()
        collection = collection.strip()
        if not model or not collection:
            raise ValueError("--dense-collection must include both MODEL and COLLECTION")
        configs.append(DenseRunConfig(model=model, collection=collection, label=f"{model}@{collection}"))
    return configs


async def evaluate_dense_run(
    samples: list[dict[str, Any]],
    dense_config: DenseRunConfig,
    reranker_models: list[str],
    candidate_k: int,
    concurrency: int,
    verbose: bool,
    progress: bool,
) -> dict[str, Any]:
    settings = get_settings()
    embedder = SentenceTransformerEmbeddingModel(dense_config.model)
    client = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=max(settings.qdrant_query_timeout_seconds, 10.0),
        check_compatibility=False,
    )
    rerankers = [
        (model_name, FlagEmbeddingRerankerModel(model_name, use_fp16=settings.reranker_use_fp16))
        for model_name in reranker_models
    ]

    try:
        case_inputs = []
        prepare_progress = ProgressBar(f"{dense_config.label} prepare", len(samples), progress)
        for index, sample in enumerate(samples, start=1):
            case_inputs.append(await _prepare_case(sample))
            prepare_progress.update(index)
        prepare_progress.close()

        all_query_texts = [
            query_text
            for case_input in case_inputs
            for query_text in case_input["query_texts"]
        ]
        query_vectors = await _embed_batches(
            embedder,
            all_query_texts,
            settings.embedding_timeout_seconds,
            progress=progress,
            label=f"{dense_config.label} embed",
        )

        vector_cursor = 0
        tasks = []
        semaphore = asyncio.Semaphore(concurrency)
        for case_input in case_inputs:
            query_count = len(case_input["query_texts"])
            vectors = query_vectors[vector_cursor : vector_cursor + query_count]
            vector_cursor += query_count
            tasks.append(
                _evaluate_case(
                    client=client,
                    collection=dense_config.collection,
                    case_input=case_input,
                    query_vectors=vectors,
                    rerankers=rerankers,
                    candidate_k=candidate_k,
                    semaphore=semaphore,
                )
            )

        rows = await collect_completed_rows(
            tasks,
            progress_label=f"{dense_config.label} evaluate",
            progress=progress,
            verbose=verbose,
        )

        summary = aggregate_rows(rows)
        return {
            "dense_model": dense_config.model,
            "collection": dense_config.collection,
            "candidate_k": candidate_k,
            "summary": summary,
            "cases": sorted(rows, key=lambda row: row["case_id"]),
            "worst_cases": _worst_cases(rows),
        }
    finally:
        await client.close()


async def collect_completed_rows(
    awaitables,
    progress_label: str,
    progress: bool,
    verbose: bool,
) -> list[dict[str, Any]]:
    tasks = [asyncio.create_task(awaitable) for awaitable in awaitables]
    rows = []
    progress_bar = ProgressBar(progress_label, len(tasks), progress)
    try:
        for index, task in enumerate(asyncio.as_completed(tasks), start=1):
            rows.append(await task)
            progress_bar.update(index)
            if verbose and index % 25 == 0:
                print(f"evaluated {index}/{len(tasks)} cases")
        return rows
    except Exception:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    finally:
        progress_bar.close()


async def _prepare_case(sample: dict[str, Any]) -> dict[str, Any]:
    user_input = sample_user_input(sample)
    request = ChatRequest(
        message=user_input,
        retrieval_options=RetrievalOptions(allow_web=False, qdrant_search=True),
    )
    normalized = normalize_input(request.message)
    decision = route_question(request)
    resolved = await resolve_entities(decision.entities, message=request.message)
    _enrich_decision_entities(decision, resolved)
    query_plan = plan_query_facets(decision, normalized)
    facet_plans = [retrieval_plan_for_facet(facet, decision) for facet in query_plan.facets]
    query_texts = [_build_hybrid_query(request.message, plan) for plan in facet_plans]
    return {
        "sample": sample,
        "decision": decision,
        "query_plan": query_plan,
        "facet_plans": facet_plans,
        "query_texts": query_texts,
    }


async def _embed_batches(
    embedder,
    query_texts: list[str],
    timeout_seconds: float,
    progress: bool = False,
    label: str = "embed",
) -> list[list[float]]:
    vectors: list[list[float]] = []
    batch_size = 64
    progress_bar = ProgressBar(label, len(query_texts), progress)
    for start in range(0, len(query_texts), batch_size):
        vectors.extend(
            await embedder.embed(
                query_texts[start : start + batch_size],
                timeout_seconds=max(timeout_seconds, 180.0),
            )
        )
        progress_bar.update(min(start + batch_size, len(query_texts)))
    progress_bar.close()
    return vectors


async def _evaluate_case(
    client: AsyncQdrantClient,
    collection: str,
    case_input: dict[str, Any],
    query_vectors: list[list[float]],
    rerankers: list[tuple[str, Any]],
    candidate_k: int,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    async with semaphore:
        sample = case_input["sample"]
        baseline = []
        for facet, plan, vector in zip(
            case_input["query_plan"].facets,
            case_input["facet_plans"],
            query_vectors,
            strict=True,
        ):
            candidates = await retrieve_candidates(
                client=client,
                collection=collection,
                plan=plan,
                query_vector=vector,
                candidate_k=candidate_k,
            )
            for candidate in candidates:
                candidate.metadata["facet_id"] = facet.intent
            baseline.extend(candidates)

        metadata = sample_metadata(sample)
        expected_references = {
            normalize_path(reference)
            for reference in metadata["expected_references"]
            if reference
        }
        row: dict[str, Any] = {
            "case_id": metadata["case_id"],
            "suite": metadata["suite"],
            "category": metadata["category"],
            "question": sample_user_input(sample),
            "intents": case_input["decision"].intents,
            "baseline": {
                **compute_reference_metrics(baseline, expected_references),
                **diagnostic_metrics(sample, baseline, max(DEFAULT_RECALL_KS)),
            },
            "top_baseline": [_candidate_summary(candidate) for candidate in baseline[: max(DEFAULT_RECALL_KS)]],
        }

        for index, (model_name, reranker) in enumerate(rerankers):
            reranked = await rerank_candidates(
                reranker=reranker,
                query=sample_user_input(sample),
                candidates=baseline,
            )
            key = f"reranked:{model_name}"
            metrics = {
                **compute_reference_metrics(reranked, expected_references),
                **diagnostic_metrics(sample, reranked, max(DEFAULT_RECALL_KS)),
            }
            row[key] = metrics
            if index == 0:
                row["reranked"] = metrics
                row["top_reranked"] = [_candidate_summary(candidate) for candidate in reranked[: max(DEFAULT_RECALL_KS)]]

        return row


async def retrieve_candidates(
    client: AsyncQdrantClient,
    collection: str,
    plan: RetrievalPlan,
    query_vector: list[float],
    candidate_k: int,
) -> list[RetrievedCandidate]:
    query_filter = _build_query_filter(plan.metadata_filters)
    sparse_query = build_sparse_vector(" ".join(_query_terms(plan)))
    try:
        response = await client.query_points(
            collection_name=collection,
            prefetch=[
                Prefetch(query=query_vector, using="dense", limit=candidate_k),
                Prefetch(query=sparse_query, using="sparse", limit=candidate_k),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            query_filter=query_filter,
            limit=candidate_k,
            with_payload=True,
        )
    except Exception as exc:
        if query_filter is None or "Index required" not in str(exc):
            raise
        response = await client.query_points(
            collection_name=collection,
            prefetch=[
                Prefetch(query=query_vector, using="dense", limit=candidate_k),
                Prefetch(query=sparse_query, using="sparse", limit=candidate_k),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            query_filter=None,
            limit=candidate_k,
            with_payload=True,
        )

    evidence_items = []
    for point in response.points:
        payload = point.payload or {}
        text = str(payload.get("text", ""))
        metadata = dict(payload)
        metadata["sparse_score"] = _sparse_score(text, plan.queries + plan.entities.get("drugs", []))
        evidence_items.append(
            EvidenceItem(
                id=str(point.id),
                text=text,
                source=str(payload.get("source", "unknown")),
                trust_tier=str(payload.get("trust_tier", "local_curated")),
                title=str(payload.get("name", payload.get("title", "Untitled"))),
                url=payload.get("url"),
                score=float(point.score),
                metadata=metadata,
            )
        )

    ranked = rerank_evidence(
        evidence_items,
        preferred_fields=plan.metadata_filters.get("field", []),
        required_entities=plan.entities.get("drugs", []),
    )
    return [_candidate_from_evidence(item) for item in ranked[:candidate_k]]


def _sparse_score(text: str, terms: list[str]) -> float:
    folded = accent_fold(text)
    if not terms:
        return 0.0
    matches = sum(1 for term in terms if accent_fold(term) in folded)
    return matches / len(terms)


async def rerank_candidates(reranker, query: str, candidates: list[RetrievedCandidate]) -> list[RetrievedCandidate]:
    if not candidates:
        return []
    scores = await reranker.score(query, [candidate.text for candidate in candidates], timeout_seconds=30.0)
    reranked = []
    for candidate, score in zip(candidates, scores, strict=True):
        metadata = dict(candidate.metadata)
        metadata["reranker_score"] = float(score)
        reranked.append(
            RetrievedCandidate(
                path=candidate.path,
                text=candidate.text,
                title=candidate.title,
                field=candidate.field,
                score=float(score),
                source=candidate.source,
                trust_tier=candidate.trust_tier,
                metadata=metadata,
            )
        )
    return sorted(reranked, key=lambda candidate: candidate.score, reverse=True)


def _candidate_from_evidence(item: EvidenceItem) -> RetrievedCandidate:
    path = normalize_path(str(item.metadata.get("path") or item.metadata.get("local_path") or ""))
    return RetrievedCandidate(
        path=path,
        text=item.text,
        title=item.title,
        field=str(item.metadata.get("field") or ""),
        score=float(item.score),
        source=item.source,
        trust_tier=item.trust_tier,
        metadata=dict(item.metadata),
    )


def _candidate_summary(candidate: RetrievedCandidate) -> dict[str, Any]:
    return {
        "title": candidate.title,
        "field": candidate.field,
        "path": candidate.path,
        "score": candidate.score,
        "source": candidate.source,
    }


def _worst_cases(rows: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    def score(row: dict[str, Any]) -> tuple[float, float, float]:
        baseline = row["baseline"]
        return (
            float(baseline.get("recall@11", 0.0)),
            float(baseline.get("mrr", 0.0)),
            float(baseline.get("precision@7", 0.0)),
        )

    return [
        {
            "case_id": row["case_id"],
            "suite": row["suite"],
            "question": row["question"],
            "intents": row["intents"],
            "baseline": row["baseline"],
            "top_baseline": row["top_baseline"][:3],
        }
        for row in sorted(rows, key=score)[:limit]
    ]


def print_summary(report: dict[str, Any]) -> None:
    for run_label, run_report in report["runs"].items():
        print(f"\n=== {run_label} ===")
        _print_metric_table("overall", run_report["summary"]["overall"])
        for suite, suite_summary in run_report["summary"]["by_suite"].items():
            _print_metric_table(suite, suite_summary)


def _print_metric_table(label: str, summary: dict[str, dict[str, float]]) -> None:
    if not summary:
        return
    print(f"\n[{label}]")
    for result_name, metrics in summary.items():
        values = " ".join(f"{name}={value:.4f}" for name, value in metrics.items())
        print(f"{result_name}: {values}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate MedChat retrieval ranking.")
    parser.add_argument("--dataset", default="evals/datasets/generated/all_suites.json")
    parser.add_argument("--suite", action="append", help="Filter to one suite; repeat for multiple suites.")
    parser.add_argument("--limit", type=int, help="Evaluate only the first N selected samples.")
    parser.add_argument("--per-suite", type=int, help="Evaluate the first N samples from each suite.")
    parser.add_argument("--collection", help="Qdrant collection for --dense-model.")
    parser.add_argument("--dense-model", help="Dense embedding model used for query embedding.")
    parser.add_argument(
        "--dense-collection",
        action="append",
        help="Evaluate a dense model against a matching collection, formatted MODEL=COLLECTION. Repeat to compare dense models.",
    )
    parser.add_argument("--reranker-model", action="append", default=[], help="Optional reranker model. Repeat to compare rerankers.")
    parser.add_argument("--candidate-k", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--output", help="Output JSON report path.")
    parser.add_argument("--no-write", action="store_true", help="Print metrics without writing a report file.")
    parser.add_argument("--no-progress", action="store_true", help="Disable terminal progress bars.")
    parser.add_argument("--verbose", action="store_true")
    return parser


async def async_main(args: argparse.Namespace) -> dict[str, Any]:
    settings = get_settings()
    dense_model = args.dense_model or settings.embedding_model
    collection = args.collection or settings.qdrant_collection
    dense_configs = parse_dense_configs(args.dense_collection, dense_model, collection)
    samples = load_dataset(
        path=Path(args.dataset),
        suites=set(args.suite) if args.suite else None,
        limit=args.limit,
        per_suite=args.per_suite,
    )
    if not samples:
        raise ValueError("No evaluation samples selected.")

    report: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset,
        "sample_count": len(samples),
        "precision_ks": list(DEFAULT_PRECISION_KS),
        "recall_ks": list(DEFAULT_RECALL_KS),
        "reranker_models": args.reranker_model,
        "runs": {},
    }
    for dense_config in dense_configs:
        if args.verbose:
            print(f"Running dense model {dense_config.model} on collection {dense_config.collection}")
        report["runs"][dense_config.label] = await evaluate_dense_run(
            samples=samples,
            dense_config=dense_config,
            reranker_models=args.reranker_model,
            candidate_k=args.candidate_k,
            concurrency=args.concurrency,
            verbose=args.verbose,
            progress=not args.no_progress and sys.stdout.isatty(),
        )
    return report


def default_output_path() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return Path("evals/reports") / f"retrieval_eval_{timestamp}.json"


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    runtime_error = ensure_project_runtime()
    if runtime_error is not None:
        print(runtime_error, file=sys.stderr)
        raise SystemExit(2)
    report = asyncio.run(async_main(args))
    print_summary(report)
    if not args.no_write:
        output = Path(args.output) if args.output else default_output_path()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nReport written to {output.as_posix()}")


if __name__ == "__main__":
    main()
