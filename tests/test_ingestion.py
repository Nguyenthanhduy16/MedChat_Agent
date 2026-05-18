from pathlib import Path
from typing import Any

import pytest

from core.ingestion import ChunkValidationError, canonicalize_chunk, load_chunk_file
from core.config import Settings
from core.text import stable_hash


class RecordingEmbeddingModel:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.input_types: list[str] = []

    async def embed(self, texts: list[str], timeout_seconds: float, input_type: str = "query") -> list[list[float]]:
        self.calls.append(texts)
        self.input_types.append(input_type)
        return [[float(index), 1.0, 2.0] for index, _ in enumerate(texts)]


class RecordingQdrantClient:
    def __init__(self) -> None:
        self.created_collections: list[dict[str, Any]] = []
        self.upserts: list[dict[str, Any]] = []

    async def collection_exists(self, collection_name: str) -> bool:
        return False

    async def create_collection(self, **kwargs: Any) -> None:
        self.created_collections.append(kwargs)

    async def upsert(self, **kwargs: Any) -> None:
        self.upserts.append(kwargs)


def test_load_chunk_file_accepts_current_corpus_shape() -> None:
    chunks = load_chunk_file(Path("tests/fixtures/chunks/abacavir.json"), "longchau_ingredients_chunked")

    assert len(chunks) == 1
    assert chunks[0].metadata["name"] == "Abacavir"
    assert chunks[0].metadata["source_family"] == "longchau_ingredients_chunked"
    assert chunks[0].metadata["local_path"] == Path("tests/fixtures/chunks/abacavir.json").as_posix()
    assert chunks[0].metadata["trust_tier"] == "local_curated"
    assert chunks[0].metadata["content_hash"] == stable_hash(chunks[0].text)
    assert chunks[0].sparse_text.startswith("hoat chat abacavir")


def test_stable_id_is_same_for_same_chunk() -> None:
    raw = {
        "text": "Hoạt chất: Abacavir",
        "metadata": {
            "name": "Abacavir",
            "id": "abacavir",
            "url": "https://example.test/abacavir",
            "type": "Dược chất",
            "source": "Fixture",
            "field": "describe",
            "chunk_index": 0,
        },
    }

    first = canonicalize_chunk(raw, "longchau_ingredients_chunked", Path("data/chunks/abacavir.json"))
    second = canonicalize_chunk(raw, "longchau_ingredients_chunked", Path("data/chunks/abacavir.json"))

    assert first.id == second.id


def test_stable_id_changes_when_normalized_text_changes() -> None:
    base = {
        "text": "Hoạt chất: Abacavir",
        "metadata": {
            "name": "Abacavir",
            "id": "abacavir",
            "url": "https://example.test/abacavir",
            "type": "Dược chất",
            "source": "Fixture",
            "field": "describe",
            "chunk_index": 0,
        },
    }
    changed = {**base, "text": "Hoạt chất: Abacavir dùng điều trị HIV"}

    first = canonicalize_chunk(base, "longchau_ingredients_chunked", Path("data/chunks/abacavir.json"))
    second = canonicalize_chunk(changed, "longchau_ingredients_chunked", Path("data/chunks/abacavir.json"))

    assert first.id != second.id


def test_encoding_repair_metadata_recorded_when_text_is_repaired() -> None:
    raw = {
        "text": "Hoáº¡t cháº¥t: Abacavir",
        "metadata": {
            "name": "Abacavir",
            "id": "abacavir",
            "url": "https://example.test/abacavir",
            "type": "Dược chất",
            "source": "Fixture",
            "field": "describe",
            "chunk_index": 0,
        },
    }

    chunk = canonicalize_chunk(raw, "longchau_ingredients_chunked", Path("data/chunks/abacavir.json"))

    assert chunk.text == "Hoạt chất: Abacavir"
    assert chunk.metadata["encoding_repaired"] is True
    assert chunk.metadata["encoding_repair_confidence"] >= 0.7


def test_hiv_is_extracted_as_condition_not_drug() -> None:
    raw = {
        "text": "Điều trị nhiễm HIV ở người lớn.",
        "metadata": {
            "name": "Abacavir",
            "id": "abacavir",
            "url": "https://example.test/abacavir",
            "type": "Dược chất",
            "source": "Fixture",
            "field": "indication",
            "chunk_index": 0,
        },
    }

    chunk = canonicalize_chunk(raw, "longchau_ingredients_chunked", Path("data/chunks/abacavir.json"))

    assert "HIV" in chunk.entities["conditions"]
    assert "HIV" not in chunk.entities["drugs"]


def test_disease_chunk_name_is_condition_not_drug() -> None:
    raw = {
        "text": "HIV là bệnh nhiễm virus cần điều trị và theo dõi.",
        "metadata": {
            "name": "HIV",
            "id": "hiv",
            "url": "https://example.test/hiv",
            "category": "Bệnh truyền nhiễm",
            "type": "Disease",
            "source": "Condition Fixture",
            "field": "overview",
            "chunk_index": 0,
        },
    }

    chunk = canonicalize_chunk(raw, "disease_conditions", Path("data/chunks/hiv.json"))

    folded_conditions = {value.lower() for value in chunk.entities["conditions"]}
    folded_drugs = {value.lower() for value in chunk.entities["drugs"]}
    assert "hiv" in folded_conditions
    assert "hiv" not in folded_drugs


def test_stable_id_changes_when_path_changes() -> None:
    raw = {
        "text": "Hoạt chất: Abacavir",
        "metadata": {
            "name": "Abacavir",
            "id": "abacavir",
            "url": "https://example.test/abacavir",
            "type": "Dược chất",
            "source": "Fixture",
            "field": "describe",
            "chunk_index": 0,
        },
    }

    first = canonicalize_chunk(raw, "longchau_ingredients_chunked", Path("data/chunks/abacavir.json"))
    second = canonicalize_chunk(raw, "longchau_ingredients_chunked", Path("data/other/abacavir.json"))

    assert first.id != second.id


def test_invalid_missing_text_rejected() -> None:
    with pytest.raises(ChunkValidationError):
        load_chunk_file(Path("tests/fixtures/chunks/invalid_missing_text.json"), "fixture")


def test_empty_required_metadata_value_rejected() -> None:
    raw = {
        "text": "Hoạt chất: Abacavir",
        "metadata": {
            "name": "",
            "id": "abacavir",
            "url": "https://example.test/abacavir",
            "type": "Dược chất",
            "source": "Fixture",
            "field": "describe",
            "chunk_index": 0,
        },
    }

    with pytest.raises(ChunkValidationError):
        canonicalize_chunk(raw, "longchau_ingredients_chunked", Path("data/chunks/abacavir.json"))


@pytest.mark.parametrize("field", ["name", "source", "type", "field"])
def test_required_string_metadata_rejects_non_strings(field: str) -> None:
    raw = {
        "text": "Hoạt chất: Abacavir",
        "metadata": {
            "name": "Abacavir",
            "id": "abacavir",
            "url": "https://example.test/abacavir",
            "type": "Dược chất",
            "source": "Fixture",
            "field": "describe",
            "chunk_index": 0,
        },
    }
    raw["metadata"][field] = 123

    with pytest.raises(ChunkValidationError):
        canonicalize_chunk(raw, "longchau_ingredients_chunked", Path("data/chunks/abacavir.json"))


@pytest.mark.parametrize("chunk_index", [1.5, "1", -1, None, True])
def test_chunk_index_rejects_invalid_values(chunk_index: object) -> None:
    raw = {
        "text": "Hoạt chất: Abacavir",
        "metadata": {
            "name": "Abacavir",
            "id": "abacavir",
            "url": "https://example.test/abacavir",
            "type": "Dược chất",
            "source": "Fixture",
            "field": "describe",
            "chunk_index": chunk_index,
        },
    }

    with pytest.raises(ChunkValidationError):
        canonicalize_chunk(raw, "longchau_ingredients_chunked", Path("data/chunks/abacavir.json"))


def test_ingest_directory_reports_indexed_and_skipped() -> None:
    from core.ingestion import ingest_directory

    report = ingest_directory(Path("tests/fixtures/chunks"))

    assert report["indexed"] == 1
    assert report["skipped"] == 1
    assert report["errors"]


@pytest.mark.asyncio
async def test_ingest_directory_async_embeds_and_upserts_to_qdrant() -> None:
    from core.ingestion import ingest_directory_async

    embedding = RecordingEmbeddingModel()
    qdrant = RecordingQdrantClient()
    settings = Settings(
        qdrant_collection="test_chunks",
        qdrant_vector_size=3,
        ingestion_batch_size=2,
        embedding_timeout_seconds=9.0,
        qdrant_upsert_timeout_seconds=7.0,
    )

    report = await ingest_directory_async(
        Path("tests/fixtures/chunks"),
        embedding_model=embedding,
        qdrant_client=qdrant,
        settings=settings,
    )

    assert report["indexed"] == 1
    assert report["skipped"] == 1
    assert report["errors"]
    assert len(embedding.calls) == 1
    assert len(embedding.calls[0]) == 1
    assert embedding.calls[0][0].startswith("Hoạt chất: Abacavir")
    assert embedding.input_types == ["passage"]
    assert qdrant.created_collections
    assert qdrant.created_collections[0]["collection_name"] == "test_chunks"
    assert qdrant.upserts[0]["collection_name"] == "test_chunks"
    assert qdrant.upserts[0]["wait"] is True
    assert qdrant.upserts[0]["timeout"] == 7
    point = qdrant.upserts[0]["points"][0]
    assert point.id
    assert point.vector == [0.0, 1.0, 2.0]
    assert point.payload["text"].startswith("Hoạt chất: Abacavir")
    assert point.payload["sparse_text"].startswith("hoat chat abacavir")
    assert point.payload["entities"]["drugs"] == ["Abacavir"]
    assert point.payload["source_family"] == "chunks"
    assert point.payload["ingested_at"].endswith("Z")
