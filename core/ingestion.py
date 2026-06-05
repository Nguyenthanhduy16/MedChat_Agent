import json
import re
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5
from datetime import UTC, datetime

from qdrant_client.http.models import Distance, Modifier, PayloadSchemaType, PointStruct, SparseVectorParams, VectorParams

from core.config import Settings, get_settings
from core.llm import EmbeddingModel
from core.models import CanonicalChunk
from core.sparse_vectors import build_sparse_vector
from core.text import accent_fold, normalize_text, repair_mojibake, slugify, stable_hash


class ChunkValidationError(ValueError):
    pass


REPAIR_CONFIDENCE_THRESHOLD = 0.7
CONDITION_TERMS = {
    "hiv": "HIV",
    "suy than": "suy thận",
    "mang thai": "mang thai",
    "cho con bu": "cho con bú",
}
CONDITION_CONTEXT_TERMS = ("disease", "benh", "condition", "symptom", "trieu chung")
INGREDIENT_CONTEXT_TERMS = ("duoc chat", "ingredient", "active substance")
PAYLOAD_INDEX_FIELDS = ("field", "trust_tier", "source_family", "name")


def _require_metadata(raw: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    metadata = raw.get("metadata")
    if not isinstance(metadata, dict):
        raise ChunkValidationError(_message("chunk metadata must be an object", path))

    required_string_fields = ("name", "source", "type", "field")
    invalid_strings = [
        field
        for field in required_string_fields
        if field not in metadata or not isinstance(metadata[field], str) or not metadata[field].strip()
    ]
    if invalid_strings:
        raise ChunkValidationError(
            _message(f"chunk metadata fields must be non-empty strings: {', '.join(invalid_strings)}", path)
        )

    if "chunk_index" not in metadata or not _is_valid_chunk_index(metadata["chunk_index"]):
        raise ChunkValidationError(_message("chunk_index must be an integer >= 0", path))
    return dict(metadata)


def _extract_entities(text: str, metadata: dict[str, Any]) -> dict[str, list[str]]:
    drugs: list[str] = []
    metadata_conditions: list[str] = []
    for key in ("name", "id"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            if _metadata_indicates_condition(metadata):
                metadata_conditions.append(normalize_text(value))
            elif _metadata_indicates_ingredient(metadata):
                drugs.append(normalize_text(value))
            else:
                drugs.append(normalize_text(value))

    category = metadata.get("category")
    fields = [str(metadata["field"])]
    if isinstance(category, str) and category.strip():
        fields.append(normalize_text(category))

    conditions = metadata_conditions + [
        canonical
        for folded_term, canonical in CONDITION_TERMS.items()
        if _contains_folded_term(text, folded_term)
    ]

    return {
        "drugs": _unique_non_empty(drugs),
        "fields": _unique_non_empty(fields),
        "conditions": _unique_non_empty(conditions),
    }


def canonicalize_chunk(raw: dict[str, Any], source_family: str, path: Path | None = None) -> CanonicalChunk:
    if not isinstance(raw, dict):
        raise ChunkValidationError(_message("chunk must be an object", path))

    raw_text = raw.get("text")
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ChunkValidationError(_message("chunk text must be a non-empty string", path))

    metadata = _require_metadata(raw, path)
    repaired_text, text_repaired, text_confidence = repair_mojibake(raw_text)
    if text_repaired and text_confidence < REPAIR_CONFIDENCE_THRESHOLD:
        raise ChunkValidationError(_message("text encoding repair confidence below threshold", path))
    text = normalize_text(repaired_text)
    content_hash = stable_hash(text)
    metadata = _canonicalize_metadata(metadata, source_family, path, content_hash)
    if text_repaired:
        metadata["encoding_repaired"] = True
        metadata["encoding_repair_confidence"] = text_confidence
    sparse_text = accent_fold(text)
    entities = _extract_entities(text, metadata)

    chunk_id = _build_chunk_id(metadata)

    return CanonicalChunk(
        id=chunk_id,
        text=text,
        sparse_text=sparse_text,
        entities=entities,
        metadata=metadata,
    )


def load_chunk_file(path: Path, source_family: str | None = None) -> list[CanonicalChunk]:
    family = source_family or path.parent.name
    try:
        raw_json = path.read_text(encoding="utf-8")
        payload = json.loads(raw_json)
    except UnicodeDecodeError as exc:
        raise ChunkValidationError(_message(f"cannot decode file as UTF-8: {exc}", path)) from exc
    except OSError as exc:
        raise ChunkValidationError(_message(f"cannot read chunk file: {exc}", path)) from exc
    except json.JSONDecodeError as exc:
        raise ChunkValidationError(_message(f"invalid JSON: {exc.msg}", path)) from exc

    if not isinstance(payload, list):
        raise ChunkValidationError(_message("chunk file must contain a JSON array", path))

    return [canonicalize_chunk(item, family, path) for item in payload]


def ingest_directory(path: Path) -> dict[str, object]:
    report: dict[str, object] = {"indexed": 0, "skipped": 0, "errors": []}
    errors: list[str] = []

    if not path.exists():
        return {"indexed": 0, "skipped": 0, "errors": [f"directory not found: {path}"]}

    for chunk_file in sorted(path.rglob("*.json")):
        source_family = chunk_file.parent.name
        try:
            chunks = load_chunk_file(chunk_file, source_family)
        except Exception as exc:
            report["skipped"] = int(report["skipped"]) + 1
            errors.append(str(exc))
            continue
        report["indexed"] = int(report["indexed"]) + len(chunks)

    report["errors"] = errors
    return report


async def ingest_directory_async(
    path: Path,
    *,
    embedding_model: EmbeddingModel,
    qdrant_client: Any,
    settings: Settings | None = None,
) -> dict[str, object]:
    active_settings = settings or get_settings()
    report: dict[str, object] = {"indexed": 0, "skipped": 0, "errors": []}
    errors: list[str] = []

    if not path.exists():
        return {"indexed": 0, "skipped": 0, "errors": [f"directory not found: {path}"]}

    await _ensure_collection(qdrant_client, active_settings)
    batch: list[CanonicalChunk] = []

    async def flush() -> None:
        nonlocal batch
        if not batch:
            return
            
        batch_ids = [chunk.id for chunk in batch]
        try:
            existing_points = await qdrant_client.retrieve(
                collection_name=active_settings.qdrant_collection,
                ids=batch_ids,
                with_payload=False,
                with_vectors=False,
            )
            existing_ids = {str(p.id) for p in existing_points}
        except Exception:
            existing_ids = set()
            
        new_batch = [chunk for chunk in batch if chunk.id not in existing_ids]
        
        if new_batch:
            vectors = await embedding_model.embed(
                [chunk.text for chunk in new_batch],
                timeout_seconds=active_settings.embedding_timeout_seconds,
                input_type="passage",
            )
            points = [
                PointStruct(
                    id=chunk.id,
                    vector={
                        "dense": vector,
                        "sparse": build_sparse_vector(chunk.sparse_text),
                    },
                    payload=_point_payload(chunk),
                )
                for chunk, vector in zip(new_batch, vectors, strict=True)
            ]
            await qdrant_client.upsert(
                collection_name=active_settings.qdrant_collection,
                points=points,
                wait=True,
                timeout=int(active_settings.qdrant_upsert_timeout_seconds)
                if active_settings.qdrant_upsert_timeout_seconds
                else None,
            )
        batch = []

    try:
        from tqdm import tqdm
        json_files = list(path.rglob("*.json"))
        file_iterator = tqdm(sorted(json_files), desc="Ingesting files", unit="file")
    except ImportError:
        file_iterator = sorted(path.rglob("*.json"))

    for chunk_file in file_iterator:
        source_family = chunk_file.parent.name
        try:
            chunks = load_chunk_file(chunk_file, source_family)
        except Exception as exc:
            report["skipped"] = int(report["skipped"]) + 1
            errors.append(str(exc))
            continue

        for chunk in chunks:
            batch.append(chunk)
            if len(batch) >= active_settings.ingestion_batch_size:
                await flush()
        report["indexed"] = int(report["indexed"]) + len(chunks)

    await flush()
    report["errors"] = errors
    return report


async def _ensure_collection(qdrant_client: Any, settings: Settings) -> None:
    exists = await qdrant_client.collection_exists(collection_name=settings.qdrant_collection)
    if not exists:
        await qdrant_client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config={
                "dense": VectorParams(size=settings.qdrant_vector_size, distance=Distance.COSINE),
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(modifier=Modifier.IDF),
            },
        )
    await _ensure_payload_indexes(qdrant_client, settings)


async def _ensure_payload_indexes(qdrant_client: Any, settings: Settings) -> None:
    for field_name in PAYLOAD_INDEX_FIELDS:
        try:
            await qdrant_client.create_payload_index(
                collection_name=settings.qdrant_collection,
                field_name=field_name,
                field_schema=PayloadSchemaType.KEYWORD,
            )
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                raise


def _point_payload(chunk: CanonicalChunk) -> dict[str, Any]:
    payload = dict(chunk.metadata)
    payload["text"] = chunk.text
    payload["sparse_text"] = chunk.sparse_text
    payload["entities"] = chunk.entities
    payload["ingested_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return payload


def _canonicalize_metadata(
    metadata: dict[str, Any],
    source_family: str,
    path: Path | None,
    content_hash: str,
) -> dict[str, Any]:
    canonical = dict(metadata)
    for key, value in list(canonical.items()):
        if isinstance(value, str):
            repaired, changed, confidence = repair_mojibake(value)
            if changed and confidence < REPAIR_CONFIDENCE_THRESHOLD:
                raise ChunkValidationError(_message(f"metadata field {key} encoding repair confidence below threshold", path))
            canonical[key] = normalize_text(repaired)

    canonical["source_family"] = normalize_text(source_family)
    canonical["local_path"] = path.as_posix() if path is not None else ""
    canonical["trust_tier"] = "local_curated"
    canonical["content_hash"] = content_hash
    canonical["source_slug"] = slugify(str(canonical["source"]))
    canonical["type_slug"] = slugify(str(canonical["type"]))
    canonical["field"] = normalize_text(str(canonical["field"]))
    canonical["chunk_index"] = _coerce_chunk_index(canonical["chunk_index"], path)
    if path is not None:
        canonical["path"] = str(path.as_posix())
    return canonical


def _coerce_chunk_index(value: Any, path: Path | None) -> int:
    if not _is_valid_chunk_index(value):
        raise ChunkValidationError(_message("chunk_index must be an integer >= 0", path))
    return value


def _is_valid_chunk_index(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _build_chunk_id(metadata: dict[str, Any]) -> str:
    id_value = metadata.get("id")
    id_or_slug = normalize_text(id_value) if isinstance(id_value, str) and id_value.strip() else slugify(str(metadata["name"]))
    identity = "|".join(
        [
            str(metadata["source_family"]),
            str(metadata["local_path"]),
            id_or_slug,
            str(metadata["field"]),
            str(metadata["chunk_index"]),
            str(metadata["content_hash"]),
        ]
    )
    return str(uuid5(NAMESPACE_URL, identity))


def _unique_non_empty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = normalize_text(value)
        key = accent_fold(normalized)
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def _contains_folded_term(text: str, folded_term: str) -> bool:
    folded = accent_fold(text)
    pattern = r"(?<![a-z0-9])" + re.escape(folded_term) + r"(?![a-z0-9])"
    return re.search(pattern, folded) is not None


def _metadata_indicates_condition(metadata: dict[str, Any]) -> bool:
    context = _metadata_context(metadata)
    return any(_contains_folded_term(context, term) for term in CONDITION_CONTEXT_TERMS)


def _metadata_indicates_ingredient(metadata: dict[str, Any]) -> bool:
    context = _metadata_context(metadata)
    return any(_contains_folded_term(context, term) for term in INGREDIENT_CONTEXT_TERMS)


def _metadata_context(metadata: dict[str, Any]) -> str:
    values = [
        metadata.get("type"),
        metadata.get("category"),
        metadata.get("source_family"),
        metadata.get("source"),
    ]
    return " ".join(value for value in values if isinstance(value, str))


def _message(message: str, path: Path | None) -> str:
    if path is None:
        return message
    return f"{path}: {message}"
