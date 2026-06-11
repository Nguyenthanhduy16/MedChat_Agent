from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import sys
import types
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from dotenv import load_dotenv
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.schemas import ChatRequest, RetrievalOptions

DEFAULT_DATASET = Path("evals/datasets/ragas_ground_truth.jsonl")
DEFAULT_METRICS = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
    "answer_correctness",
)


@dataclass(frozen=True)
class RagasEvalSample:
    case_id: str
    question: str
    reference: str
    category: str | None
    metadata: dict[str, Any]


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
        if self.enabled:
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


def load_samples(path: Path, limit: int | None) -> list[RagasEvalSample]:
    raw_samples = _read_dataset(path)
    samples = [_sample_from_mapping(sample, index) for index, sample in enumerate(raw_samples, start=1)]
    if limit is not None:
        samples = samples[:limit]
    if not samples:
        raise ValueError(f"No RAGAS samples found in {path.as_posix()}")
    return samples


def _read_dataset(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return []
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    payload = json.loads(text)
    if isinstance(payload, list):
        return [sample for sample in payload if isinstance(sample, dict)]
    if isinstance(payload, dict):
        return [payload]
    raise ValueError(f"Unsupported RAGAS dataset format: {path.as_posix()}")


def _sample_from_mapping(sample: dict[str, Any], index: int) -> RagasEvalSample:
    question = _sample_question(sample)
    reference = _sample_reference(sample)
    metadata = _sample_metadata(sample)
    return RagasEvalSample(
        case_id=str(metadata.get("case_id") or sample.get("case_id") or f"sample-{index:04d}"),
        question=question,
        reference=reference,
        category=_optional_str(metadata.get("category") or sample.get("category") or sample.get("question_type")),
        metadata=metadata,
    )


def _sample_question(sample: dict[str, Any]) -> str:
    if isinstance(sample.get("user_input"), str):
        return sample["user_input"]
    input_block = sample.get("input")
    if isinstance(input_block, dict) and isinstance(input_block.get("user_input"), str):
        return input_block["user_input"]
    raise ValueError(f"Unsupported RAGAS sample schema; missing user_input keys={sorted(sample.keys())}")


def _sample_reference(sample: dict[str, Any]) -> str:
    for key in ("reference", "ground_truth", "expected_answer"):
        if isinstance(sample.get(key), str):
            return sample[key]
        if isinstance(sample.get(key), dict):
            for nested_key in ("answer", "reference", "expected_answer"):
                if isinstance(sample[key].get(nested_key), str):
                    return sample[key][nested_key]
    evaluation = sample.get("evaluation")
    if isinstance(evaluation, dict):
        for key in ("answer", "reference", "expected_answer"):
            if isinstance(evaluation.get(key), str):
                return evaluation[key]
    raise ValueError(f"Unsupported RAGAS sample schema; missing reference keys={sorted(sample.keys())}")


def _sample_metadata(sample: dict[str, Any]) -> dict[str, Any]:
    rubric = sample.get("rubric")
    if isinstance(rubric, dict):
        return dict(rubric)
    metadata = {
        key: sample[key]
        for key in ("case_id", "suite", "category", "question_type")
        if key in sample
    }
    evaluation = sample.get("evaluation")
    if isinstance(evaluation, dict):
        metadata.update({f"evaluation_{key}": value for key, value in evaluation.items() if isinstance(value, str | int | float | bool)})
    return metadata


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


async def build_ragas_rows(
    samples: list[RagasEvalSample],
    chat_service: Any,
    progress: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    progress_bar = ProgressBar("answer cases", len(samples), progress)
    try:
        for index, sample in enumerate(samples, start=1):
            response = await chat_service.chat(
                ChatRequest(
                    message=sample.question,
                    retrieval_options=RetrievalOptions(allow_web=False, qdrant_search=True),
                )
            )
            contexts = [citation.snippet for citation in response.citations if citation.snippet]
            rows.append(
                {
                    "user_input": sample.question,
                    "response": response.answer,
                    "retrieved_contexts": contexts,
                    "reference": sample.reference,
                }
            )
            cases.append(
                {
                    "case_id": sample.case_id,
                    "category": sample.category,
                    "question": sample.question,
                    "reference": sample.reference,
                    "answer": response.answer,
                    "citation_count": len(response.citations),
                    "citations": [citation.model_dump() for citation in response.citations],
                    "intents": response.intents,
                    "risk_level": response.risk_level,
                    "evidence_status": response.evidence_status,
                    "confidence": response.confidence,
                    "warnings": response.warnings,
                    "metadata": sample.metadata,
                }
            )
            progress_bar.update(index)
    finally:
        progress_bar.close()
    return rows, cases


def run_ragas_evaluation(rows: list[dict[str, Any]], metric_names: list[str], show_progress: bool = True):
    try:
        prime_native_imports()
        _install_ragas_vertexai_import_shim()
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics.collections import (
            answer_correctness,
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
    except Exception as exc:
        raise RuntimeError(
            "Unable to import RAGAS evaluation dependencies. "
            "Install/repair ragas and its langchain dependencies in the project .venv, then retry."
        ) from exc

    metric_map = {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
        "context_recall": context_recall,
        "answer_correctness": answer_correctness,
    }
    unknown = sorted(set(metric_names) - set(metric_map))
    if unknown:
        raise ValueError(f"Unsupported RAGAS metrics: {', '.join(unknown)}")
    dataset = Dataset.from_list(rows)
    return evaluate(
        dataset,
        metrics=[metric_map[name] for name in metric_names],
        show_progress=show_progress,
        raise_exceptions=False,
    )


def _install_ragas_vertexai_import_shim() -> None:
    module_name = "langchain_community.chat_models.vertexai"
    if module_name in sys.modules:
        return
    try:
        __import__(module_name)
        return
    except ModuleNotFoundError:
        pass

    shim = types.ModuleType(module_name)

    class ChatVertexAI:
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError(
                "ChatVertexAI is unavailable in this environment. "
                "Install langchain-google-vertexai or use a non-VertexAI RAGAS judge."
            )

    shim.ChatVertexAI = ChatVertexAI
    sys.modules[module_name] = shim


def prime_native_imports() -> None:
    """Import pyarrow before transformer/FlagEmbedding imports on Windows."""
    try:
        importlib.import_module("pyarrow")
    except ModuleNotFoundError:
        return


def result_to_records(result: Any, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metric_columns = _result_metric_columns(result)
    records: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        record = {"case_id": case["case_id"]}
        for metric_name, values in metric_columns.items():
            record[metric_name] = values[index] if index < len(values) else None
        records.append(record)
    return records


def _result_metric_columns(result: Any) -> dict[str, list[Any]]:
    if isinstance(result, dict):
        return {key: list(value) if isinstance(value, list | tuple) else [value] for key, value in result.items()}
    if hasattr(result, "to_pandas"):
        frame = result.to_pandas()
        return {column: frame[column].tolist() for column in frame.columns if column not in {"user_input", "response", "retrieved_contexts", "reference"}}
    if hasattr(result, "scores"):
        scores = result.scores
        if isinstance(scores, list):
            columns: dict[str, list[Any]] = {}
            for score in scores:
                if isinstance(score, dict):
                    for key, value in score.items():
                        columns.setdefault(key, []).append(value)
            return columns
    raise TypeError(f"Unsupported RAGAS result type: {type(result)!r}")


def summarize_metric_records(records: list[dict[str, Any]]) -> dict[str, float]:
    metric_names = sorted({key for record in records for key in record if key != "case_id"})
    summary: dict[str, float] = {}
    for metric_name in metric_names:
        values = [
            float(record[metric_name])
            for record in records
            if isinstance(record.get(metric_name), int | float)
        ]
        if values:
            summary[metric_name] = mean(values)
    return summary


def build_report(
    dataset: Path,
    samples: list[RagasEvalSample],
    cases: list[dict[str, Any]],
    metric_records: list[dict[str, Any]],
    metric_names: Iterable[str],
) -> dict[str, Any]:
    metrics_by_case = {record["case_id"]: {key: value for key, value in record.items() if key != "case_id"} for record in metric_records}
    report_cases = []
    for case in cases:
        case = dict(case)
        case["metrics"] = metrics_by_case.get(case["case_id"], {})
        report_cases.append(case)
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": dataset.as_posix(),
        "sample_count": len(samples),
        "metrics": list(metric_names),
        "summary": summarize_metric_records(metric_records),
        "cases": report_cases,
    }


def default_output_path() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return Path("evals/reports") / f"ragas_eval_{timestamp}.json"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate MedChat answer quality with RAGAS.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET.as_posix())
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--metric", action="append", choices=DEFAULT_METRICS, help="RAGAS metric to run; repeat to select multiple.")
    parser.add_argument("--llm-model", help="Model name for RAGAS/OpenAI-compatible judge, passed via RAGAS_LLM_MODEL and OPENAI_MODEL_NAME.")
    parser.add_argument("--embedding-model", help="Embedding model name for RAGAS defaults, passed via RAGAS_EMBEDDING_MODEL.")
    parser.add_argument("--no-progress", action="store_true")
    return parser


async def async_main(args: argparse.Namespace) -> dict[str, Any]:
    if args.llm_model:
        os.environ["RAGAS_LLM_MODEL"] = args.llm_model
        os.environ["OPENAI_MODEL_NAME"] = args.llm_model
    if args.embedding_model:
        os.environ["RAGAS_EMBEDDING_MODEL"] = args.embedding_model

    prime_native_imports()

    from backend.api.routes import get_chat_service

    dataset = Path(args.dataset)
    metric_names = args.metric or list(DEFAULT_METRICS)
    samples = load_samples(dataset, limit=args.limit)
    rows, cases = await build_ragas_rows(samples, get_chat_service(), progress=not args.no_progress)
    result = run_ragas_evaluation(rows, metric_names, show_progress=not args.no_progress)
    metric_records = result_to_records(result, cases)
    return build_report(dataset, samples, cases, metric_records, metric_names)


def print_summary(report: dict[str, Any]) -> None:
    print("\n[RAGAS summary]")
    summary = report.get("summary", {})
    if not summary:
        return
    metric_names = list(summary.keys())
    metric_width = max(len("metric"), *(len(name) for name in metric_names))
    score_width = len("score")
    score_values = [f"{float(summary[name]):.4f}" for name in metric_names]
    score_width = max(score_width, *(len(value) for value in score_values))

    def format_row(metric: str, score: str, score_align: str = ">") -> str:
        if score_align == "<":
            return f"| {metric:<{metric_width}} | {score:<{score_width}} |"
        return f"| {metric:<{metric_width}} | {score:>{score_width}} |"

    print(format_row("metric", "score", score_align="<"))
    print(f"| {'-' * metric_width} | {'-' * score_width} |")
    for name, value in zip(metric_names, score_values, strict=True):
        print(format_row(name, value))


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    report = asyncio.run(async_main(args))
    print_summary(report)
    if not args.no_write:
        output = Path(args.output) if args.output else default_output_path()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nReport written to {output.as_posix()}")


if __name__ == "__main__":
    main()
