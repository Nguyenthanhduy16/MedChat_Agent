from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

try:
    import pyarrow
except ImportError:
    pass


def configure_transformer_runtime() -> None:
    os.environ.setdefault("USE_TF", "0")
    os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    # Suppress HuggingFace fast-tokenizer advisory printed to stderr.
    # PowerShell treats any stderr output as an error and aborts the script.
    import warnings
    warnings.filterwarnings("ignore", message=".*fast tokenizer.*")
    warnings.filterwarnings("ignore", message=".*XLMRoberta.*")


configure_transformer_runtime()

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
from qdrant_client.http.models import Fusion, FusionQuery, Prefetch

from backend.api.schemas import ChatRequest, RetrievalOptions
from backend.api.routes import _build_chat_model
from core.agent import route_question
from core.chat_service import _build_hybrid_query, _enrich_decision_entities
from core.config import get_settings
from core.entity_resolver import resolve_entities
from core.llm import FlagEmbeddingRerankerModel, SentenceTransformerEmbeddingModel
from core.models import EvidenceItem, RetrievalPlan
from core.query_planner import plan_query_facets, retrieval_plan_for_facet
from core.retrieval import _build_query_filter, _query_terms, rerank_evidence
from core.router_classifier import LLMRouterClassifier
from core.sparse_vectors import build_sparse_vector
from core.text import accent_fold
from core.input_normalizer import normalize_input


DEFAULT_PRECISION_KS = (3, 5, 7)
DEFAULT_RECALL_KS = (5, 7, 9, 11)
DIAGNOSTIC_K = 5

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
        self.update(0)

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


def normalize_eval_path(value: str | None) -> str:
    path = normalize_path(value).strip("/")
    for prefix in ("data/chunked/", "./data/chunked/"):
        if path.startswith(prefix):
            return path[len(prefix) :]
    return path


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
        metadata.get("chunk_id"),
        metadata.get("content_hash"),
    ):
        if value:
            keys.add(normalize_path(str(value)))

    path = normalize_path(str(metadata.get("path") or metadata.get("local_path") or candidate.path))
    slug = Path(path).stem if path else ""
    id_val = str(metadata.get("id") or "")
    field_name = str(metadata.get("field") or candidate.field or "")
    chunk_index = metadata.get("chunk_index")
    
    if field_name and chunk_index is not None:
        for entity_type in ("drug", "condition", "supplement", "ingredient"):
            if slug:
                keys.add(f"{entity_type}:{slug}:{field_name}:{chunk_index}")
            if id_val:
                keys.add(f"{entity_type}:{id_val}:{field_name}:{chunk_index}")
                
        type_slug = str(metadata.get("type_slug") or metadata.get("type") or "").strip()
        if type_slug:
            if slug:
                keys.add(f"{type_slug}:{slug}:{field_name}:{chunk_index}")
            if id_val:
                keys.add(f"{type_slug}:{id_val}:{field_name}:{chunk_index}")

        normalized_parts = Path(normalize_eval_path(path)).parts
        if len(normalized_parts) >= 3 and normalized_parts[0] == "pharmacity_chunked" and slug:
            keys.add(f"pharmacity:{normalized_parts[1]}:{slug}:{field_name}:{chunk_index}")
                
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
    expected_categories = _expected_categories(sample)
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
        f"category_hit@{k}": _has_category_hit(top_k, expected_categories) if expected_categories else False,
        f"category_field_hit@{k}": (
            _has_category_field_hit(top_k, expected_categories, expected_fields)
            if expected_categories and expected_fields
            else False
        ),
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


def _expected_categories(sample: dict[str, Any]) -> set[str]:
    expected_retrieval = sample.get("expected_retrieval")
    categories = set()
    if isinstance(expected_retrieval, dict):
        for source_file in expected_retrieval.get("source_files", []):
            path = normalize_eval_path(str(source_file))
            if path:
                categories.add(Path(path).parent.as_posix())
    
    if not categories:
        for context in sample.get("reference_contexts", []):
            if isinstance(context, dict):
                source_file = context.get("source_file")
                if source_file:
                    path = normalize_eval_path(str(source_file))
                    if path:
                        categories.add(Path(path).parent.as_posix())
                    
    return categories


def _candidate_category(candidate: RetrievedCandidate) -> str:
    path = normalize_eval_path(str(candidate.metadata.get("path") or candidate.path))
    return Path(path).parent.as_posix() if path else ""


def _has_category_hit(candidates: list[RetrievedCandidate], expected_categories: set[str]) -> bool:
    return any(_candidate_category(candidate) in expected_categories for candidate in candidates)


def _has_category_field_hit(
    candidates: list[RetrievedCandidate],
    expected_categories: set[str],
    expected_fields: set[str],
) -> bool:
    return any(
        _candidate_category(candidate) in expected_categories
        and (candidate.field or "") in expected_fields
        for candidate in candidates
    )


def load_dataset(path: Path, suites: set[str] | None, limit: int | None, per_suite: int | None) -> list[dict[str, Any]]:
    samples = json.loads(path.read_text(encoding="utf-8"))
    if suites:
        samples = [sample for sample in samples if sample_metadata(sample)["suite"] in suites]
    if per_suite is not None:
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for sample in samples:
            suite = str(sample_metadata(sample)["suite"])
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
    reranker_device: str,
    reranker_use_fp16: bool,
    reranker_batch_size: int,
    candidate_k: int,
    concurrency: int,
    verbose: bool,
    progress: bool,
    router_classifier: LLMRouterClassifier | None = None,
    router_timeout_seconds: float = 8.0,
) -> dict[str, Any]:
    settings = get_settings()
    client = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=max(settings.qdrant_query_timeout_seconds, 60.0),
        check_compatibility=False,
    )
    rerankers = []
    for model_name in reranker_models:
        if verbose or progress:
            print(f"Loading reranker model: {model_name}... (this may take a while to download)")
        # core/llm.py sets TRANSFORMERS_OFFLINE=1 and HF_HUB_OFFLINE=1 at module level.
        # FlagEmbedding crashes with an access violation when these are set during model init.
        # Temporarily clear them so FlagReranker can load model weights, then restore.
        _saved_offline = {
            k: os.environ.pop(k, None)
            for k in ("TRANSFORMERS_OFFLINE", "HF_HUB_OFFLINE")
        }
        try:
            rerankers.append((
                model_name,
                FlagEmbeddingRerankerModel(
                    model_name,
                    use_fp16=reranker_use_fp16,
                    device=reranker_device,
                    batch_size=reranker_batch_size,
                ),
            ))
        finally:
            for k, v in _saved_offline.items():
                if v is not None:
                    os.environ[k] = v

    embedder = SentenceTransformerEmbeddingModel(dense_config.model)

    try:
        case_inputs = []
        prepare_progress = ProgressBar(f"{dense_config.label} prepare", len(samples), progress)
        for index, sample in enumerate(samples, start=1):
            case_inputs.append(
                await _prepare_case(
                    sample,
                    router_classifier=router_classifier,
                    router_timeout_seconds=router_timeout_seconds,
                )
            )
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
        await apply_rerankers_to_rows(rows, rerankers, progress=progress)
        _strip_internal_candidates(rows)

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


async def _prepare_case(
    sample: dict[str, Any],
    router_classifier=None,
    router_timeout_seconds: float = 8.0,
) -> dict[str, Any]:
    user_input = sample_user_input(sample)
    request = ChatRequest(
        message=user_input,
        retrieval_options=RetrievalOptions(allow_web=False, qdrant_search=True),
    )
    normalized = normalize_input(request.message)
    fallback_decision = route_question(request)
    if router_classifier is not None:
        decision = await router_classifier.classify(
            request,
            normalized=normalized,
            fallback_decision=fallback_decision,
            timeout_seconds=router_timeout_seconds,
        )
    else:
        decision = fallback_decision
        decision.classification_uncertain = False
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
                **diagnostic_metrics(sample, baseline, DIAGNOSTIC_K),
            },
            "top_baseline": [_candidate_summary(candidate) for candidate in baseline[: DIAGNOSTIC_K]],
            "_expected_references": expected_references,
            "_sample": sample,
            "_baseline_candidates": baseline,
        }

        return row


async def apply_rerankers_to_rows(
    rows: list[dict[str, Any]],
    rerankers: list[tuple[str, Any]],
    progress: bool,
) -> None:
    if not rerankers:
        return

    for index, (model_name, reranker) in enumerate(rerankers):
        total_pairs = sum(len(row.get("_baseline_candidates", [])) for row in rows)
        progress_bar = ProgressBar(f"{model_name} rerank", total_pairs, progress)
        completed_pairs = 0
        try:
            for row in rows:
                candidates = list(row.get("_baseline_candidates", []))
                reranked = await rerank_candidates(
                    reranker=reranker,
                    query=str(row["question"]),
                    candidates=candidates,
                )
                metrics = {
                    **compute_reference_metrics(reranked, set(row.get("_expected_references", set()))),
                    **diagnostic_metrics(row["_sample"], reranked, DIAGNOSTIC_K),
                }
                key = f"reranked:{model_name}"
                row[key] = metrics
                row[f"top_{key}"] = [_candidate_summary(candidate) for candidate in reranked[: DIAGNOSTIC_K]]
                if index == 0:
                    row["reranked"] = metrics
                    row["top_reranked"] = row[f"top_{key}"]

                completed_pairs += len(candidates)
                progress_bar.update(completed_pairs)
        finally:
            progress_bar.close()


def _strip_internal_candidates(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        row.pop("_expected_references", None)
        row.pop("_sample", None)
        row.pop("_baseline_candidates", None)


async def retrieve_candidates(
    client: AsyncQdrantClient,
    collection: str,
    plan: RetrievalPlan,
    query_vector: list[float],
    candidate_k: int,
) -> list[RetrievedCandidate]:
    query_filter = _build_query_filter(plan.metadata_filters)
    sparse_query = build_sparse_vector(" ".join(_query_terms(plan)))
    query_kwargs = {
        "collection_name": collection,
        "prefetch": [
            Prefetch(query=query_vector, using="dense", limit=candidate_k),
            Prefetch(query=sparse_query, using="sparse", limit=candidate_k),
        ],
        "query": FusionQuery(fusion=Fusion.RRF),
        "limit": candidate_k,
        "with_payload": True,
    }
    try:
        response = await _query_points_with_retry(client, {**query_kwargs, "query_filter": query_filter})
    except Exception as exc:
        if query_filter is None or "Index required" not in str(exc):
            raise
        response = await _query_points_with_retry(client, {**query_kwargs, "query_filter": None})

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


async def _query_points_with_retry(client: AsyncQdrantClient, kwargs: dict[str, Any], attempts: int = 3):
    last_exc: ResponseHandlingException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await client.query_points(**kwargs)
        except ResponseHandlingException as exc:
            last_exc = exc
            if attempt == attempts or not _is_transient_qdrant_error(exc):
                raise
            await asyncio.sleep(0.25 * attempt)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Qdrant query retry exhausted without an exception")


def _is_transient_qdrant_error(exc: ResponseHandlingException) -> bool:
    text = str(exc).lower()
    return (
        "timeout" in text
        or "timed out" in text
        or "temporarily unavailable" in text
        or "connection reset" in text
    )


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
    metric_names: list[str] = []
    for metrics in summary.values():
        for name in metrics:
            if name not in metric_names:
                metric_names.append(name)

    result_names = list(summary.keys())
    headers = ["metric", *result_names]

    col_widths = [len(h) for h in headers]
    for name in metric_names:
        col_widths[0] = max(col_widths[0], len(name))
        for i, result_name in enumerate(result_names, start=1):
            val_str = f"{summary[result_name][name]:.4f}" if name in summary[result_name] else ""
            col_widths[i] = max(col_widths[i], len(val_str))

    def format_row(row: list[str]) -> str:
        formatted = [f"{row[0]:<{col_widths[0]}}"]
        for i, val in enumerate(row[1:], start=1):
            formatted.append(f"{val:>{col_widths[i]}}")
        return "| " + " | ".join(formatted) + " |"

    print(format_row(headers))
    sep_row = ["-" * col_widths[0]] + ["-" * col_widths[i] for i in range(1, len(col_widths))]
    print("| " + " | ".join(sep_row) + " |")

    for name in metric_names:
        values = [f"{summary[result_name][name]:.4f}" if name in summary[result_name] else "" for result_name in result_names]
        print(format_row([name, *values]))


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
    parser.add_argument(
        "--reranker-device",
        choices=("auto", "cuda", "cpu"),
        help="Device for FlagEmbedding rerankers. Use cpu if CUDA model loading hangs.",
    )
    parser.add_argument("--reranker-batch-size", type=int, help="Batch size for FlagEmbedding reranker scoring.")
    parser.add_argument("--no-reranker-fp16", action="store_true", help="Disable fp16 for reranker scoring.")
    parser.add_argument("--candidate-k", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--output", help="Output JSON report path.")
    parser.add_argument("--no-write", action="store_true", help="Print metrics without writing a report file.")
    parser.add_argument("--no-progress", action="store_true", help="Disable terminal progress bars.")
    parser.add_argument("--llm-router", action="store_true", help="Use the configured LLM router during query planning.")
    parser.add_argument("--verbose", action="store_true")
    return parser


async def async_main(args: argparse.Namespace) -> dict[str, Any]:
    settings = get_settings()
    dense_model = args.dense_model or settings.embedding_model
    collection = args.collection or settings.qdrant_collection
    reranker_device = args.reranker_device or settings.reranker_device
    reranker_batch_size = args.reranker_batch_size or settings.reranker_batch_size
    reranker_use_fp16 = settings.reranker_use_fp16 and not args.no_reranker_fp16
    router_classifier = build_eval_router_classifier(settings) if args.llm_router else None
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
        "router": "llm" if args.llm_router else "rule_based",
        "runs": {},
    }
    for dense_config in dense_configs:
        if args.verbose:
            print(f"Running dense model {dense_config.model} on collection {dense_config.collection}")
        report["runs"][dense_config.label] = await evaluate_dense_run(
            samples=samples,
            dense_config=dense_config,
            reranker_models=args.reranker_model,
            reranker_device=reranker_device,
            reranker_use_fp16=reranker_use_fp16,
            reranker_batch_size=reranker_batch_size,
            candidate_k=args.candidate_k,
            concurrency=args.concurrency,
            verbose=args.verbose,
            progress=not args.no_progress and sys.stdout.isatty(),
            router_classifier=router_classifier,
            router_timeout_seconds=settings.llm_router_timeout_seconds,
        )
    return report


def build_eval_router_classifier(settings) -> LLMRouterClassifier:
    router_model = _build_chat_model(settings, model_override=settings.router_model)
    return LLMRouterClassifier(
        router_model,
        confidence_threshold=settings.llm_router_confidence_threshold,
    )


def default_output_path() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return Path("evals/reports") / f"retrieval_eval_{timestamp}.json"


def main() -> None:
    logging.getLogger("core.router_classifier").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.ERROR)
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
