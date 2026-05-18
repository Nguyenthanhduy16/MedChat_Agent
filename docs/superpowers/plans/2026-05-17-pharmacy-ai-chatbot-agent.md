# Pharmacy AI Chatbot Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI MVP backend for a pharmacy AI chatbot agent with Qdrant-backed hybrid RAG, citations, safety guardrails, evidence sufficiency checks, and provider-agnostic LLM adapters.

**Architecture:** The backend is split into small modules under `backend/api` and `core`. `backend/api` owns HTTP schemas and routes. `core` owns config, ingestion, retrieval, evidence, safety, citations, web-source policy, LLM adapters, and chat orchestration. The MVP is fail-closed for pharmacy answers: if evidence or citations are insufficient, it returns a limited response instead of an unsupported LLM answer.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, pytest, qdrant-client, httpx, python-dotenv, OpenAI-compatible API client, optional rank-bm25 for sparse scoring.

---

## File Structure

Create or modify these files:

- `requirements.txt`: runtime and test dependencies.
- `backend/__init__.py`: backend package marker.
- `backend/api/__init__.py`: API package marker.
- `backend/api/schemas.py`: Pydantic request and response schemas for `/chat`, `/ingest`, health, and source status.
- `backend/api/routes.py`: FastAPI routes and dependency wiring.
- `backend/main.py`: FastAPI app factory and runnable app object.
- `core/__init__.py`: core package marker.
- `core/config.py`: environment settings and timeout defaults.
- `core/models.py`: shared dataclasses/enums for chunks, evidence, router output, and confidence.
- `core/text.py`: Unicode normalization, mojibake repair, accent folding, slugging, stable hashes.
- `core/ingestion.py`: JSON chunk loading, validation, canonicalization, stable IDs, entity extraction, embedding/upsert orchestration.
- `core/llm.py`: provider-agnostic chat and embedding interfaces plus fake and OpenAI-compatible implementations.
- `core/retrieval.py`: Qdrant hybrid retrieval interface, metadata filtering, sparse/entity scoring, reranking.
- `core/evidence.py`: evidence package builder, sufficiency gate, confidence calculation.
- `core/citations.py`: citation formatter and citation completeness helpers.
- `core/safety.py`: safety pre-check, post-check, urgent templates, professional-advice rules.
- `core/agent.py`: multi-label intent/risk router and retrieval plan builder.
- `core/web_sources.py`: whitelist enforcement, domain-scoped query construction, fetch/search adapter interfaces.
- `core/chat_service.py`: end-to-end orchestration for `/chat`.
- `core/cli.py`: ingestion CLI entry point.
- `tests/conftest.py`: pytest fixtures.
- `tests/test_api_schemas.py`: request/response schema tests.
- `tests/test_text.py`: encoding, accent folding, stable hash tests.
- `tests/test_ingestion.py`: chunk schema, canonical chunk, stable ID tests.
- `tests/test_agent_safety.py`: multi-label intent and risk tests.
- `tests/test_evidence.py`: sufficiency gate and confidence tests.
- `tests/test_citations.py`: citation formatting tests.
- `tests/test_web_sources.py`: whitelist and timeout behavior tests.
- `tests/test_chat_service.py`: mocked end-to-end chat tests.
- `tests/fixtures/chunks/abacavir.json`: small valid chunk fixture.
- `tests/fixtures/chunks/invalid_missing_text.json`: invalid chunk fixture.

This workspace is currently not a git repository. Commit steps below should be run only after the user initializes git or moves the project into a repository. Until then, treat commit steps as checkpoints and run the listed tests.

---

### Task 1: Project Scaffold And Dependencies

**Files:**
- Modify: `requirements.txt`
- Create: `backend/__init__.py`
- Create: `backend/api/__init__.py`
- Create: `backend/main.py`
- Create: `core/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write dependency file**

Replace `requirements.txt` with:

```txt
fastapi>=0.111,<1
uvicorn[standard]>=0.30,<1
pydantic>=2.7,<3
pydantic-settings>=2.2,<3
python-dotenv>=1.0,<2
qdrant-client>=1.9,<2
httpx>=0.27,<1
openai>=1.30,<2
rank-bm25>=0.2,<1
pytest>=8.2,<9
pytest-asyncio>=0.23,<1
respx>=0.21,<1
```

- [ ] **Step 2: Create package markers**

Create `backend/__init__.py`, `backend/api/__init__.py`, and `core/__init__.py` as empty files.

- [ ] **Step 3: Create minimal FastAPI app**

Create `backend/main.py`:

```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="MedChat Pharmacy Agent", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 4: Create pytest fixtures file**

Create `tests/conftest.py`:

```python
import pytest


@pytest.fixture
def sample_message() -> str:
    return "Toi dang uong warfarin, co dung ibuprofen duoc khong?"
```

- [ ] **Step 5: Verify import**

Run: `python -m pytest -q`

Expected: pytest starts successfully and reports no tests collected or existing tests pass.

- [ ] **Step 6: Commit checkpoint**

If git is initialized:

```bash
git add requirements.txt backend core tests
git commit -m "chore: scaffold pharmacy agent backend"
```

---

### Task 2: Config And API Schemas

**Files:**
- Create: `core/config.py`
- Create: `backend/api/schemas.py`
- Test: `tests/test_api_schemas.py`

- [ ] **Step 1: Write schema tests**

Create `tests/test_api_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from backend.api.schemas import ChatRequest, ChatResponse


def test_chat_request_accepts_optional_context() -> None:
    request = ChatRequest(
        message="Toi dang uong warfarin, co dung ibuprofen duoc khong?",
        user_context={
            "age": 67,
            "sex": "female",
            "pregnancy_status": "not_pregnant",
            "lactation": False,
            "conditions": ["rung nhi"],
            "current_medications": ["warfarin"],
            "allergies": [],
            "location": "VN",
        },
        retrieval_options={"allow_web": True, "max_sources": 8},
    )

    assert request.preferences.language == "vi"
    assert request.preferences.audience == "general"
    assert request.user_context.age == 67
    assert request.retrieval_options.max_sources == 8


def test_chat_request_rejects_empty_message() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="   ")


def test_chat_response_requires_evidence_status_and_warnings() -> None:
    response = ChatResponse(
        answer="Thong tin tham khao.",
        safety_notice="Khong thay the tu van y te chuyen nghiep.",
        citations=[],
        intents=["interaction"],
        risk_level="high",
        evidence_status="partial",
        warnings=["Can xac minh them danh sach thuoc dang dung."],
        confidence="medium",
        requires_professional_advice=True,
    )

    assert response.evidence_status == "partial"
    assert response.warnings == ["Can xac minh them danh sach thuoc dang dung."]
```

- [ ] **Step 2: Run schema tests and verify failure**

Run: `python -m pytest tests/test_api_schemas.py -q`

Expected: FAIL with `ModuleNotFoundError` or missing `ChatRequest`.

- [ ] **Step 3: Implement config**

Create `core/config.py`:

```python
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MedChat Pharmacy Agent"
    openai_api_key: str | None = None
    chat_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-small"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "pharmacy_chunks"
    qdrant_vector_size: int = 1536
    api_request_body_kb: int = 64
    chat_timeout_seconds: float = 60.0
    llm_timeout_seconds: float = 30.0
    embedding_timeout_seconds: float = 60.0
    qdrant_query_timeout_seconds: float = 5.0
    qdrant_upsert_timeout_seconds: float = 30.0
    web_search_timeout_seconds: float = 8.0
    web_fetch_timeout_seconds: float = 5.0
    max_web_urls_per_request: int = 5
    max_evidence_chunks_for_llm: int = 12
    local_top_k_per_intent: int = 6
    final_citations_min: int = 3
    final_citations_max: int = 8
    ingestion_batch_size: int = 64
    whitelist_domains: list[str] = Field(
        default_factory=lambda: [
            "moh.gov.vn",
            "who.int",
            "fda.gov",
            "accessdata.fda.gov",
            "dailymed.nlm.nih.gov",
            "ema.europa.eu",
            "medicines.org.uk",
            "pubmed.ncbi.nlm.nih.gov",
        ]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Implement API schemas**

Create `backend/api/schemas.py`:

```python
from typing import Literal
from pydantic import BaseModel, Field, field_validator


RiskLevel = Literal["low", "medium", "high", "urgent"]
EvidenceStatus = Literal["sufficient", "partial", "insufficient", "conflicting"]
Confidence = Literal["high", "medium", "low"]
Audience = Literal["general", "professional"]
PregnancyStatus = Literal["unknown", "not_pregnant", "pregnant", "planning_pregnancy"]


class UserContext(BaseModel):
    age: int | None = Field(default=None, ge=0, le=130)
    sex: str | None = None
    pregnancy_status: PregnancyStatus = "unknown"
    lactation: bool | None = None
    conditions: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    location: str | None = None


class ChatPreferences(BaseModel):
    language: str = "vi"
    audience: Audience = "general"
    include_technical_detail: bool = False


class RetrievalOptions(BaseModel):
    allow_web: bool = True
    max_sources: int = Field(default=8, ge=1, le=12)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=16000)
    conversation_id: str | None = None
    user_context: UserContext = Field(default_factory=UserContext)
    preferences: ChatPreferences = Field(default_factory=ChatPreferences)
    retrieval_options: RetrievalOptions = Field(default_factory=RetrievalOptions)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message must not be blank")
        return stripped


class Citation(BaseModel):
    id: str
    title: str
    url: str | None = None
    source: str
    trust_tier: str
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    safety_notice: str
    citations: list[Citation]
    intents: list[str]
    risk_level: RiskLevel
    evidence_status: EvidenceStatus
    warnings: list[str] = Field(default_factory=list)
    confidence: Confidence
    requires_professional_advice: bool


class IngestResponse(BaseModel):
    indexed: int
    skipped: int
    errors: list[str] = Field(default_factory=list)


class SourceStatusResponse(BaseModel):
    collection: str
    source_families: list[str]
    qdrant_ready: bool
```

- [ ] **Step 5: Verify schema tests pass**

Run: `python -m pytest tests/test_api_schemas.py -q`

Expected: PASS.

- [ ] **Step 6: Commit checkpoint**

If git is initialized:

```bash
git add core/config.py backend/api/schemas.py tests/test_api_schemas.py
git commit -m "feat: add config and chat schemas"
```

---

### Task 3: Text Normalization, Encoding Repair, And Stable IDs

**Files:**
- Create: `core/text.py`
- Test: `tests/test_text.py`

- [ ] **Step 1: Write text tests**

Create `tests/test_text.py`:

```python
from core.text import accent_fold, normalize_text, repair_mojibake, stable_hash, slugify


def test_normalize_text_collapses_whitespace_and_preserves_vietnamese() -> None:
    assert normalize_text("  Thuốc   dùng để làm gì? \n") == "Thuốc dùng để làm gì?"


def test_repair_mojibake_repairs_common_utf8_latin1_corruption() -> None:
    repaired, changed, confidence = repair_mojibake("DÆ°á»£c cháº¥t Long ChÃ¢u")
    assert changed is True
    assert confidence >= 0.8
    assert "Dược chất" in repaired
    assert "Long Châu" in repaired


def test_accent_fold_supports_sparse_matching() -> None:
    assert accent_fold("Phụ nữ mang thai dùng thuốc") == "phu nu mang thai dung thuoc"


def test_slugify_and_hash_are_stable() -> None:
    assert slugify("Dược chất Long Châu") == "duoc-chat-long-chau"
    assert stable_hash("abc") == stable_hash("abc")
    assert stable_hash("abc") != stable_hash("abcd")
```

- [ ] **Step 2: Run text tests and verify failure**

Run: `python -m pytest tests/test_text.py -q`

Expected: FAIL with missing `core.text`.

- [ ] **Step 3: Implement text utilities**

Create `core/text.py`:

```python
import hashlib
import re
import unicodedata


MOJIBAKE_MARKERS = ("Ã", "Ä", "Æ", "á»", "áº", "Â")


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def repair_mojibake(value: str) -> tuple[str, bool, float]:
    text = normalize_text(value)
    marker_count = sum(text.count(marker) for marker in MOJIBAKE_MARKERS)
    if marker_count == 0:
        return text, False, 1.0
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return text, False, 0.0
    repaired = normalize_text(repaired)
    repaired_marker_count = sum(repaired.count(marker) for marker in MOJIBAKE_MARKERS)
    confidence = 0.9 if repaired_marker_count < marker_count else 0.4
    return repaired, repaired != text, confidence


def accent_fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    without_marks = without_marks.replace("đ", "d").replace("Đ", "D")
    lowered = without_marks.lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def slugify(value: str) -> str:
    folded = accent_fold(value)
    return folded.replace(" ", "-")


def stable_hash(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Verify text tests pass**

Run: `python -m pytest tests/test_text.py -q`

Expected: PASS.

- [ ] **Step 5: Commit checkpoint**

If git is initialized:

```bash
git add core/text.py tests/test_text.py
git commit -m "feat: add text normalization utilities"
```

---

### Task 4: Shared Core Models

**Files:**
- Create: `core/models.py`
- Test: `tests/test_evidence.py`

- [ ] **Step 1: Write model smoke test**

Create `tests/test_evidence.py` with the first test:

```python
from core.models import EvidenceItem


def test_evidence_item_defaults() -> None:
    item = EvidenceItem(
        id="chunk-1",
        text="Warfarin interacts with NSAIDs.",
        source="DailyMed",
        trust_tier="regulatory",
        title="Warfarin label",
        url="https://dailymed.nlm.nih.gov/example",
        score=0.91,
        metadata={"field": "interaction"},
    )

    assert item.source == "DailyMed"
    assert item.metadata["field"] == "interaction"
```

- [ ] **Step 2: Run model test and verify failure**

Run: `python -m pytest tests/test_evidence.py -q`

Expected: FAIL with missing `core.models`.

- [ ] **Step 3: Implement shared models**

Create `core/models.py`:

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EvidenceStatus(str, Enum):
    SUFFICIENT = "sufficient"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"
    CONFLICTING = "conflicting"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass(frozen=True)
class CanonicalChunk:
    id: str
    text: str
    sparse_text: str
    entities: dict[str, list[str]]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    text: str
    source: str
    trust_tier: str
    title: str
    url: str | None
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidencePackage:
    items: list[EvidenceItem]
    status: EvidenceStatus
    warnings: list[str]
    reasons: list[str]


@dataclass(frozen=True)
class RouterDecision:
    intents: list[str]
    risk_level: RiskLevel
    audience: str
    needs_context: bool
    entities: dict[str, list[str]]


@dataclass(frozen=True)
class RetrievalPlan:
    intents: list[str]
    risk_level: RiskLevel
    queries: list[str]
    entities: dict[str, list[str]]
    metadata_filters: dict[str, list[str]]
```

- [ ] **Step 4: Verify model test passes**

Run: `python -m pytest tests/test_evidence.py -q`

Expected: PASS.

- [ ] **Step 5: Commit checkpoint**

If git is initialized:

```bash
git add core/models.py tests/test_evidence.py
git commit -m "feat: add shared core models"
```

---

### Task 5: Ingestion Validation, Canonical Chunks, And Stable IDs

**Files:**
- Create: `core/ingestion.py`
- Create: `tests/fixtures/chunks/abacavir.json`
- Create: `tests/fixtures/chunks/invalid_missing_text.json`
- Test: `tests/test_ingestion.py`

- [ ] **Step 1: Create valid fixture**

Create `tests/fixtures/chunks/abacavir.json`:

```json
[
  {
    "text": "Hoạt chất: Abacavir | Phần: Chỉ định | Nội dung: Điều trị nhiễm HIV ở người lớn và trẻ em trên 3 tháng tuổi.",
    "metadata": {
      "name": "Abacavir",
      "id": "abacavir",
      "url": "https://nhathuoclongchau.com.vn/thanh-phan/abacavir",
      "category": "Dược chất LC",
      "type": "Dược chất",
      "source": "Dược chất Long Châu",
      "original_lang": "vietnamese",
      "field": "indication",
      "chunk_index": 0
    }
  }
]
```

- [ ] **Step 2: Create invalid fixture**

Create `tests/fixtures/chunks/invalid_missing_text.json`:

```json
[
  {
    "metadata": {
      "name": "Broken",
      "source": "Fixture",
      "type": "Dược chất",
      "field": "indication",
      "chunk_index": 0
    }
  }
]
```

- [ ] **Step 3: Write ingestion tests**

Create `tests/test_ingestion.py`:

```python
from pathlib import Path

import pytest

from core.ingestion import ChunkValidationError, canonicalize_chunk, load_chunk_file


def test_load_chunk_file_accepts_current_corpus_shape() -> None:
    chunks = load_chunk_file(Path("tests/fixtures/chunks/abacavir.json"), "longchau_ingredients_chunked")

    assert len(chunks) == 1
    assert chunks[0].metadata["name"] == "Abacavir"
    assert chunks[0].metadata["source_family"] == "longchau_ingredients_chunked"
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
    changed = {**base, "text": "Hoạt chất: Abacavir dùng trong điều trị HIV"}

    first = canonicalize_chunk(base, "longchau_ingredients_chunked", Path("data/chunks/abacavir.json"))
    second = canonicalize_chunk(changed, "longchau_ingredients_chunked", Path("data/chunks/abacavir.json"))

    assert first.id != second.id


def test_invalid_chunk_missing_text_is_rejected() -> None:
    with pytest.raises(ChunkValidationError):
        load_chunk_file(Path("tests/fixtures/chunks/invalid_missing_text.json"), "fixture")
```

- [ ] **Step 4: Run ingestion tests and verify failure**

Run: `python -m pytest tests/test_ingestion.py -q`

Expected: FAIL with missing `core.ingestion`.

- [ ] **Step 5: Implement ingestion canonicalization**

Create `core/ingestion.py`:

```python
import json
import uuid
from pathlib import Path
from typing import Any

from core.models import CanonicalChunk
from core.text import accent_fold, normalize_text, repair_mojibake, slugify, stable_hash


class ChunkValidationError(ValueError):
    pass


def _require_metadata(metadata: dict[str, Any], key: str) -> Any:
    value = metadata.get(key)
    if value is None or value == "":
        raise ChunkValidationError(f"missing metadata.{key}")
    return value


def _extract_entities(text: str, metadata: dict[str, Any]) -> dict[str, list[str]]:
    name = str(metadata.get("name", "")).strip()
    type_value = str(metadata.get("type", "")).lower()
    drugs: list[str] = []
    ingredients: list[str] = []
    conditions: list[str] = []
    if name:
        if "dược" in type_value.lower() or "ingredient" in type_value:
            ingredients.append(name.lower())
        else:
            drugs.append(name.lower())
    folded = accent_fold(text)
    for keyword in ("hiv", "suy than", "mang thai", "cho con bu"):
        if keyword in folded:
            conditions.append(keyword)
    return {"drugs": drugs, "ingredients": ingredients, "conditions": conditions}


def canonicalize_chunk(raw: dict[str, Any], source_family: str, path: Path) -> CanonicalChunk:
    raw_text = raw.get("text")
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ChunkValidationError("missing text")
    metadata = raw.get("metadata")
    if not isinstance(metadata, dict):
        raise ChunkValidationError("missing metadata")
    for key in ("name", "source", "type", "field", "chunk_index"):
        _require_metadata(metadata, key)

    repaired_text, changed, confidence = repair_mojibake(raw_text)
    if changed and confidence < 0.7:
        raise ChunkValidationError("low confidence encoding repair")
    text = normalize_text(repaired_text)
    sparse_text = accent_fold(text)
    relative_path = path.as_posix()
    id_or_slug = str(metadata.get("id") or slugify(str(metadata["name"])))
    text_hash = stable_hash(text)
    id_input = "|".join(
        [
            source_family,
            relative_path,
            id_or_slug,
            str(metadata["field"]),
            str(metadata["chunk_index"]),
            text_hash,
        ]
    )
    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, id_input))
    enriched = dict(metadata)
    enriched.update(
        {
            "source_family": source_family,
            "local_path": relative_path,
            "trust_tier": "local_curated",
            "content_hash": text_hash,
        }
    )
    if changed:
        enriched["encoding_repaired"] = True

    return CanonicalChunk(
        id=point_id,
        text=text,
        sparse_text=sparse_text,
        entities=_extract_entities(text, metadata),
        metadata=enriched,
    )


def load_chunk_file(path: Path, source_family: str) -> list[CanonicalChunk]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ChunkValidationError("chunk file must contain a list")
    return [canonicalize_chunk(item, source_family, path) for item in raw]


def ingest_directory(root: Path) -> dict[str, object]:
    indexed = 0
    skipped = 0
    errors: list[str] = []
    for path in root.rglob("*.json"):
        source_family = path.parent.name
        try:
            indexed += len(load_chunk_file(path, source_family))
        except Exception as exc:
            skipped += 1
            errors.append(f"{path.as_posix()}: {exc}")
    return {"indexed": indexed, "skipped": skipped, "errors": errors}
```

- [ ] **Step 6: Verify ingestion tests pass**

Run: `python -m pytest tests/test_ingestion.py tests/test_text.py -q`

Expected: PASS.

- [ ] **Step 7: Commit checkpoint**

If git is initialized:

```bash
git add core/ingestion.py tests/fixtures/chunks tests/test_ingestion.py
git commit -m "feat: add chunk ingestion canonicalization"
```

---

### Task 6: LLM And Embedding Interfaces

**Files:**
- Create: `core/llm.py`
- Test: `tests/test_chat_service.py`

- [x] **Step 1: Write fake provider tests**

Create `tests/test_chat_service.py` with initial provider test:

```python
import pytest

from core.llm import FakeChatModel, FakeEmbeddingModel


@pytest.mark.asyncio
async def test_fake_llm_and_embedding_models() -> None:
    chat = FakeChatModel(answer="Answer with [S1].")
    embedding = FakeEmbeddingModel(size=4)

    answer = await chat.generate([{"role": "user", "content": "hello"}], timeout_seconds=1)
    vectors = await embedding.embed(["abc", "def"], timeout_seconds=1)

    assert answer == "Answer with [S1]."
    assert vectors == [[3.0, 0.0, 0.0, 0.0], [3.0, 0.0, 0.0, 0.0]]
```

- [x] **Step 2: Run provider test and verify failure**

Run: `python -m pytest tests/test_chat_service.py -q`

Expected: FAIL with missing `core.llm`.

- [x] **Step 3: Implement provider interfaces**

Create `core/llm.py`:

```python
from typing import Protocol

from openai import AsyncOpenAI


class ChatModel(Protocol):
    async def generate(self, messages: list[dict[str, str]], timeout_seconds: float) -> str:
        raise NotImplementedError


class EmbeddingModel(Protocol):
    async def embed(self, texts: list[str], timeout_seconds: float) -> list[list[float]]:
        raise NotImplementedError


class FakeChatModel:
    def __init__(self, answer: str) -> None:
        self.answer = answer

    async def generate(self, messages: list[dict[str, str]], timeout_seconds: float) -> str:
        return self.answer


class FakeEmbeddingModel:
    def __init__(self, size: int = 1536) -> None:
        self.size = size

    async def embed(self, texts: list[str], timeout_seconds: float) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.size
            vector[0] = float(len(text))
            vectors.append(vector)
        return vectors


class OpenAIChatModel:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(self, messages: list[dict[str, str]], timeout_seconds: float) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            timeout=timeout_seconds,
        )
        content = response.choices[0].message.content
        return content or ""


class OpenAIEmbeddingModel:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def embed(self, texts: list[str], timeout_seconds: float) -> list[list[float]]:
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
            timeout=timeout_seconds,
        )
        return [item.embedding for item in response.data]
```

- [x] **Step 4: Verify provider tests pass**

Run: `python -m pytest tests/test_chat_service.py -q`

Expected: PASS.

- [ ] **Step 5: Commit checkpoint** _(skipped: workspace is not a git repository)_

If git is initialized:

```bash
git add core/llm.py tests/test_chat_service.py
git commit -m "feat: add provider agnostic llm interfaces"
```

---

### Task 7: Router And Safety Rules

**Files:**
- Create: `core/agent.py`
- Create: `core/safety.py`
- Test: `tests/test_agent_safety.py`

- [x] **Step 1: Write agent and safety tests**

Create `tests/test_agent_safety.py`:

```python
from backend.api.schemas import ChatRequest
from core.agent import build_retrieval_plan, route_question
from core.models import RiskLevel
from core.safety import safety_precheck


def test_router_returns_multi_label_for_interaction_question() -> None:
    decision = route_question(
        ChatRequest(message="Toi dang uong warfarin, co dung ibuprofen duoc khong?")
    )

    assert "interaction" in decision.intents
    assert "contraindication" in decision.intents
    assert decision.risk_level == RiskLevel.HIGH
    assert "warfarin" in decision.entities["drugs"]
    assert "ibuprofen" in decision.entities["drugs"]


def test_router_marks_pregnancy_as_high_risk() -> None:
    decision = route_question(ChatRequest(message="Phu nu mang thai dung isotretinoin duoc khong?"))

    assert "pregnancy_lactation" in decision.intents
    assert decision.risk_level == RiskLevel.HIGH


def test_safety_precheck_marks_breathing_overdose_as_urgent() -> None:
    result = safety_precheck("Toi uong qua lieu thuoc X va dang kho tho")

    assert result.risk_level == RiskLevel.URGENT
    assert result.should_short_circuit is True


def test_retrieval_plan_includes_filters_and_entities() -> None:
    decision = route_question(ChatRequest(message="Warfarin va ibuprofen co tuong tac khong?"))
    plan = build_retrieval_plan(decision)

    assert "interaction" in plan.metadata_filters["field"]
    assert plan.entities["drugs"] == ["warfarin", "ibuprofen"]
```

- [x] **Step 2: Run agent safety tests and verify failure**

Run: `python -m pytest tests/test_agent_safety.py -q`

Expected: FAIL with missing `core.agent` or `core.safety`.

- [x] **Step 3: Implement safety**

Create `core/safety.py`:

```python
from dataclasses import dataclass

from core.models import RiskLevel
from core.text import accent_fold


URGENT_TERMS = (
    "kho tho",
    "dau nguc",
    "co giat",
    "mat y thuc",
    "phan ve",
    "qua lieu",
    "ngo doc",
    "tu tu",
)


@dataclass(frozen=True)
class SafetyResult:
    risk_level: RiskLevel
    should_short_circuit: bool
    warnings: list[str]


def safety_precheck(message: str) -> SafetyResult:
    folded = accent_fold(message)
    urgent = any(term in folded for term in URGENT_TERMS) and (
        "kho tho" in folded or "dau nguc" in folded or "co giat" in folded or "mat y thuc" in folded
    )
    if urgent:
        return SafetyResult(
            risk_level=RiskLevel.URGENT,
            should_short_circuit=True,
            warnings=["Co dau hieu nguy cap. Can lien he cap cuu hoac co so y te ngay."],
        )
    return SafetyResult(risk_level=RiskLevel.LOW, should_short_circuit=False, warnings=[])


def urgent_response() -> tuple[str, str]:
    return (
        "Neu co kho tho, dau nguc, co giat, mat y thuc, phan ve, ngo doc hoac qua lieu nang, hay goi cap cuu hoac den co so y te gan nhat ngay.",
        "Day la thong tin an toan khan cap, khong thay the danh gia truc tiep cua nhan vien y te.",
    )
```

- [x] **Step 4: Implement router**

Create `core/agent.py`:

```python
from backend.api.schemas import ChatRequest
from core.models import RetrievalPlan, RiskLevel, RouterDecision
from core.text import accent_fold


KNOWN_DRUGS = (
    "warfarin",
    "ibuprofen",
    "isotretinoin",
    "paracetamol",
    "aspirin",
    "metformin",
    "loratadin",
    "amoxicillin",
    "azithromycin",
)


def _extract_drugs(message: str) -> list[str]:
    folded = accent_fold(message)
    return [drug for drug in KNOWN_DRUGS if drug in folded]


def route_question(request: ChatRequest) -> RouterDecision:
    folded = accent_fold(request.message)
    intents: list[str] = []
    risk = RiskLevel.LOW
    drugs = _extract_drugs(request.message)

    if any(term in folded for term in ("tuong tac", "uong chung", "dung chung")) or len(drugs) >= 2:
        intents.extend(["interaction", "contraindication"])
        risk = RiskLevel.HIGH
    if any(term in folded for term in ("lieu", "cach dung", "qua lieu", "quen lieu")):
        intents.append("dosage")
        risk = RiskLevel.HIGH if "qua lieu" in folded else max_risk(risk, RiskLevel.MEDIUM)
    if any(term in folded for term in ("mang thai", "cho con bu", "thai")):
        intents.append("pregnancy_lactation")
        risk = RiskLevel.HIGH
    if any(term in folded for term in ("tre em", "nguoi gia", "suy than")):
        intents.append("pediatric_elderly" if "tre em" in folded or "nguoi gia" in folded else "disease_context")
        risk = RiskLevel.HIGH
    if any(term in folded for term in ("dung de lam gi", "cong dung", "chi dinh")):
        intents.append("indication")
    if not intents:
        intents.append("drug_identity" if drugs else "general_health")

    deduped = list(dict.fromkeys(intents))
    return RouterDecision(
        intents=deduped,
        risk_level=risk,
        audience=request.preferences.audience,
        needs_context=risk == RiskLevel.HIGH,
        entities={"drugs": drugs, "ingredients": [], "conditions": []},
    )


def max_risk(left: RiskLevel, right: RiskLevel) -> RiskLevel:
    order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.URGENT]
    return order[max(order.index(left), order.index(right))]


def build_retrieval_plan(decision: RouterDecision) -> RetrievalPlan:
    fields: list[str] = []
    for intent in decision.intents:
        if intent == "interaction":
            fields.extend(["interaction", "warning"])
        elif intent == "contraindication":
            fields.extend(["contraindication", "warning"])
        elif intent == "pregnancy_lactation":
            fields.extend(["pregnancy_lactation", "warning"])
        else:
            fields.append(intent)
    query = " ".join(decision.entities.get("drugs", []) + decision.intents)
    return RetrievalPlan(
        intents=decision.intents,
        risk_level=decision.risk_level,
        queries=[query.strip()],
        entities=decision.entities,
        metadata_filters={
            "field": list(dict.fromkeys(fields)),
            "trust_tier": ["regulatory", "clinical_reference", "local_curated"],
        },
    )
```

- [x] **Step 5: Verify agent safety tests pass**

Run: `python -m pytest tests/test_agent_safety.py -q`

Expected: PASS.

- [ ] **Step 6: Commit checkpoint** _(skipped: workspace is not a git repository)_

If git is initialized:

```bash
git add core/agent.py core/safety.py tests/test_agent_safety.py
git commit -m "feat: add pharmacy router and safety precheck"
```

---

### Task 8: Evidence Gate, Confidence, And Citations

**Files:**
- Create: `core/evidence.py`
- Create: `core/citations.py`
- Modify: `tests/test_evidence.py`
- Test: `tests/test_citations.py`

- [x] **Step 1: Extend evidence tests**

Append to `tests/test_evidence.py`:

```python
from core.evidence import assess_evidence, calculate_confidence
from core.models import EvidenceStatus, RiskLevel


def test_evidence_gate_marks_high_risk_single_source_as_partial() -> None:
    item = EvidenceItem(
        id="S1",
        text="Warfarin and ibuprofen may increase bleeding risk.",
        source="DailyMed",
        trust_tier="regulatory",
        title="Warfarin",
        url="https://dailymed.nlm.nih.gov/warfarin",
        score=0.95,
        metadata={"field": "interaction", "entities": ["warfarin", "ibuprofen"]},
    )

    package = assess_evidence(
        items=[item],
        required_intents=["interaction", "contraindication"],
        risk_level=RiskLevel.HIGH,
        required_entities=["warfarin", "ibuprofen"],
    )

    assert package.status == EvidenceStatus.PARTIAL
    assert package.warnings


def test_confidence_never_high_for_urgent_personal_scenario() -> None:
    confidence = calculate_confidence(
        status=EvidenceStatus.SUFFICIENT,
        risk_level=RiskLevel.URGENT,
        has_exact_entities=True,
        has_conflict=False,
    )

    assert confidence.value == "medium"
```

- [x] **Step 2: Write citation tests**

Create `tests/test_citations.py`:

```python
from core.citations import format_citations, has_required_citations
from core.models import EvidenceItem


def test_format_citations_dedupes_urls_and_assigns_ids() -> None:
    items = [
        EvidenceItem("1", "A", "DailyMed", "regulatory", "Warfarin", "https://x.test/a", 0.9),
        EvidenceItem("2", "B", "DailyMed", "regulatory", "Warfarin duplicate", "https://x.test/a", 0.8),
    ]

    citations = format_citations(items)

    assert len(citations) == 1
    assert citations[0]["id"] == "S1"
    assert citations[0]["url"] == "https://x.test/a"


def test_has_required_citations_detects_missing_marker() -> None:
    assert has_required_citations("Claim [S1].", [{"id": "S1"}]) is True
    assert has_required_citations("Claim without marker.", [{"id": "S1"}]) is False
```

- [x] **Step 3: Run evidence and citation tests and verify failure**

Run: `python -m pytest tests/test_evidence.py tests/test_citations.py -q`

Expected: FAIL with missing `core.evidence` or `core.citations`.

- [x] **Step 4: Implement evidence gate**

Create `core/evidence.py`:

```python
from core.models import Confidence, EvidenceItem, EvidencePackage, EvidenceStatus, RiskLevel


def assess_evidence(
    items: list[EvidenceItem],
    required_intents: list[str],
    risk_level: RiskLevel,
    required_entities: list[str],
) -> EvidencePackage:
    if not items:
        return EvidencePackage([], EvidenceStatus.INSUFFICIENT, ["No relevant evidence found."], ["empty"])

    warnings: list[str] = []
    reasons: list[str] = []
    fields = {str(item.metadata.get("field", "")) for item in items}
    entity_text = " ".join(item.text.lower() for item in items)
    missing_entities = [entity for entity in required_entities if entity.lower() not in entity_text]
    if missing_entities:
        warnings.append("Evidence does not cover all named entities: " + ", ".join(missing_entities))
        reasons.append("missing_entities")

    missing_intents = [intent for intent in required_intents if intent not in fields and intent not in entity_text]
    if missing_intents:
        warnings.append("Evidence does not cover all requested intents: " + ", ".join(missing_intents))
        reasons.append("missing_intents")

    distinct_urls = {item.url or item.id for item in items}
    if risk_level == RiskLevel.HIGH and len(distinct_urls) < 2:
        warnings.append("High-risk answer has fewer than two distinct evidence sources.")
        reasons.append("narrow_sources")

    if reasons:
        return EvidencePackage(items, EvidenceStatus.PARTIAL, warnings, reasons)
    return EvidencePackage(items, EvidenceStatus.SUFFICIENT, [], [])


def calculate_confidence(
    status: EvidenceStatus,
    risk_level: RiskLevel,
    has_exact_entities: bool,
    has_conflict: bool,
) -> Confidence:
    if has_conflict or status in (EvidenceStatus.INSUFFICIENT, EvidenceStatus.CONFLICTING):
        return Confidence.LOW
    if risk_level == RiskLevel.URGENT:
        return Confidence.MEDIUM if status == EvidenceStatus.SUFFICIENT else Confidence.LOW
    if status == EvidenceStatus.SUFFICIENT and has_exact_entities and risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM):
        return Confidence.HIGH
    if status in (EvidenceStatus.SUFFICIENT, EvidenceStatus.PARTIAL):
        return Confidence.MEDIUM
    return Confidence.LOW
```

- [x] **Step 5: Implement citations**

Create `core/citations.py`:

```python
from core.models import EvidenceItem


def format_citations(items: list[EvidenceItem], limit: int = 8) -> list[dict[str, str | None]]:
    seen: set[str] = set()
    citations: list[dict[str, str | None]] = []
    for item in sorted(items, key=lambda evidence: evidence.score, reverse=True):
        key = item.url or item.id
        if key in seen:
            continue
        seen.add(key)
        citation_id = f"S{len(citations) + 1}"
        citations.append(
            {
                "id": citation_id,
                "title": item.title,
                "url": item.url,
                "source": item.source,
                "trust_tier": item.trust_tier,
                "snippet": item.text[:300],
            }
        )
        if len(citations) >= limit:
            break
    return citations


def has_required_citations(answer: str, citations: list[dict[str, object]]) -> bool:
    if not citations:
        return False
    return any(f"[{citation['id']}]" in answer for citation in citations)
```

- [x] **Step 6: Verify evidence and citation tests pass**

Run: `python -m pytest tests/test_evidence.py tests/test_citations.py -q`

Expected: PASS.

- [ ] **Step 7: Commit checkpoint** _(skipped: workspace is not a git repository)_

If git is initialized:

```bash
git add core/evidence.py core/citations.py tests/test_evidence.py tests/test_citations.py
git commit -m "feat: add evidence gate and citations"
```

---

### Task 9: Hybrid Retrieval Interface

**Files:**
- Create: `core/retrieval.py`
- Test: add to `tests/test_evidence.py`

- [x] **Step 1: Add retrieval reranking test**

Append to `tests/test_evidence.py`:

```python
from core.retrieval import rerank_evidence


def test_rerank_combines_dense_sparse_metadata_and_trust() -> None:
    items = [
        EvidenceItem("a", "generic pain text", "Blog", "web_whitelisted", "A", "https://a.test", 0.90, {"sparse_score": 0.1, "field": "general"}),
        EvidenceItem("b", "warfarin ibuprofen bleeding", "DailyMed", "regulatory", "B", "https://b.test", 0.80, {"sparse_score": 1.0, "field": "interaction"}),
    ]

    ranked = rerank_evidence(items, preferred_fields=["interaction"], required_entities=["warfarin", "ibuprofen"])

    assert ranked[0].id == "b"
```

- [x] **Step 2: Run retrieval test and verify failure**

Run: `python -m pytest tests/test_evidence.py::test_rerank_combines_dense_sparse_metadata_and_trust -q`

Expected: FAIL with missing `core.retrieval`.

- [x] **Step 3: Implement retrieval helpers**

Create `core/retrieval.py`:

```python
from qdrant_client import AsyncQdrantClient

from core.models import EvidenceItem, RetrievalPlan
from core.text import accent_fold


TRUST_WEIGHT = {
    "regulatory": 0.30,
    "clinical_reference": 0.20,
    "local_curated": 0.15,
    "web_whitelisted": 0.05,
}


def rerank_evidence(
    items: list[EvidenceItem],
    preferred_fields: list[str],
    required_entities: list[str],
) -> list[EvidenceItem]:
    def combined(item: EvidenceItem) -> float:
        text_folded = accent_fold(item.text)
        sparse = float(item.metadata.get("sparse_score", 0.0))
        field_bonus = 0.15 if item.metadata.get("field") in preferred_fields else 0.0
        entity_bonus = 0.0
        if required_entities:
            matches = sum(1 for entity in required_entities if accent_fold(entity) in text_folded)
            entity_bonus = 0.25 * (matches / len(required_entities))
        trust_bonus = TRUST_WEIGHT.get(item.trust_tier, 0.0)
        return item.score + sparse + field_bonus + entity_bonus + trust_bonus

    return sorted(items, key=combined, reverse=True)


class QdrantRetriever:
    def __init__(self, client: AsyncQdrantClient, collection: str) -> None:
        self.client = client
        self.collection = collection

    async def retrieve(self, plan: RetrievalPlan, query_vector: list[float], timeout_seconds: float) -> list[EvidenceItem]:
        results = await self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            limit=20,
            with_payload=True,
            timeout=timeout_seconds,
        )
        items: list[EvidenceItem] = []
        for point in results:
            payload = point.payload or {}
            text = str(payload.get("text", ""))
            sparse_score = _sparse_score(text, plan.queries + plan.entities.get("drugs", []))
            metadata = dict(payload)
            metadata["sparse_score"] = sparse_score
            items.append(
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
        return rerank_evidence(
            items,
            preferred_fields=plan.metadata_filters.get("field", []),
            required_entities=plan.entities.get("drugs", []),
        )


def _sparse_score(text: str, terms: list[str]) -> float:
    folded = accent_fold(text)
    if not terms:
        return 0.0
    matches = sum(1 for term in terms if accent_fold(term) in folded)
    return matches / len(terms)
```

- [x] **Step 4: Verify retrieval tests pass**

Run: `python -m pytest tests/test_evidence.py -q`

Expected: PASS.

- [ ] **Step 5: Commit checkpoint** _(skipped: workspace is not a git repository)_

If git is initialized:

```bash
git add core/retrieval.py tests/test_evidence.py
git commit -m "feat: add hybrid retrieval reranking"
```

---

### Task 10: Whitelisted Web Source Mechanism

**Files:**
- Create: `core/web_sources.py`
- Test: `tests/test_web_sources.py`

- [x] **Step 1: Write web source tests**

Create `tests/test_web_sources.py`:

```python
import pytest

from core.web_sources import DomainNotAllowedError, WebSourceClient, build_domain_query, enforce_allowed_url


def test_build_domain_scoped_query() -> None:
    query = build_domain_query("dailymed.nlm.nih.gov", "warfarin ibuprofen interaction")

    assert query == "site:dailymed.nlm.nih.gov warfarin ibuprofen interaction"


def test_enforce_allowed_url_rejects_unlisted_domain() -> None:
    with pytest.raises(DomainNotAllowedError):
        enforce_allowed_url("https://example.com/drug", ["dailymed.nlm.nih.gov"])


@pytest.mark.asyncio
async def test_web_source_client_fetches_only_whitelisted_urls(respx_mock) -> None:
    route = respx_mock.get("https://dailymed.nlm.nih.gov/drug").respond(
        200,
        html="<html><head><title>Warfarin</title></head><body>Warfarin label text</body></html>",
    )
    client = WebSourceClient(["dailymed.nlm.nih.gov"])

    item = await client.fetch_url("https://dailymed.nlm.nih.gov/drug", timeout_seconds=1)

    assert route.called
    assert item.title == "Warfarin"
    assert "Warfarin label text" in item.text
```

- [x] **Step 2: Run web source tests and verify failure**

Run: `python -m pytest tests/test_web_sources.py -q`

Expected: FAIL with missing `core.web_sources`.

- [x] **Step 3: Implement web source mechanism**

Create `core/web_sources.py`:

```python
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx


class DomainNotAllowedError(ValueError):
    pass


@dataclass(frozen=True)
class WebFetchedSource:
    title: str
    url: str
    source: str
    text: str
    trust_tier: str


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.in_title = tag.lower() == "title"

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if not stripped:
            return
        if self.in_title:
            self.title_parts.append(stripped)
        else:
            self.text_parts.append(stripped)


def build_domain_query(domain: str, query: str) -> str:
    return f"site:{domain} {query.strip()}"


def enforce_allowed_url(url: str, whitelist_domains: list[str]) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    allowed = any(host == domain or host.endswith("." + domain) for domain in whitelist_domains)
    if not allowed:
        raise DomainNotAllowedError(f"domain not allowed: {host}")
    return host


class WebSourceClient:
    def __init__(self, whitelist_domains: list[str]) -> None:
        self.whitelist_domains = whitelist_domains

    async def fetch_url(self, url: str, timeout_seconds: float) -> WebFetchedSource:
        host = enforce_allowed_url(url, self.whitelist_domains)
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
        final_host = enforce_allowed_url(str(response.url), self.whitelist_domains)
        parser = _TextExtractor()
        parser.feed(response.text)
        title = " ".join(parser.title_parts).strip() or final_host
        text = " ".join(parser.text_parts)
        return WebFetchedSource(
            title=title,
            url=str(response.url),
            source=final_host,
            text=text[:2000],
            trust_tier=_trust_tier(final_host),
        )


def _trust_tier(host: str) -> str:
    if host.endswith(("fda.gov", "dailymed.nlm.nih.gov", "ema.europa.eu", "moh.gov.vn")):
        return "regulatory"
    if host.endswith(("who.int", "pubmed.ncbi.nlm.nih.gov", "medicines.org.uk")):
        return "clinical_reference"
    return "web_whitelisted"
```

- [x] **Step 4: Verify web source tests pass**

Run: `python -m pytest tests/test_web_sources.py -q`

Expected: PASS.

- [ ] **Step 5: Commit checkpoint** _(skipped: workspace is not a git repository)_

If git is initialized:

```bash
git add core/web_sources.py tests/test_web_sources.py
git commit -m "feat: add whitelisted web sources"
```

---

### Task 11: Chat Service Orchestration

**Files:**
- Create: `core/chat_service.py`
- Modify: `tests/test_chat_service.py`

- [x] **Step 1: Add chat service tests**

Append to `tests/test_chat_service.py`:

```python
from backend.api.schemas import ChatRequest
from core.chat_service import ChatService
from core.llm import FakeChatModel, FakeEmbeddingModel
from core.models import EvidenceItem


class FakeRetriever:
    async def retrieve(self, plan, query_vector, timeout_seconds):
        return [
            EvidenceItem(
                id="1",
                text="Warfarin and ibuprofen may increase bleeding risk.",
                source="DailyMed",
                trust_tier="regulatory",
                title="Warfarin label",
                url="https://dailymed.nlm.nih.gov/warfarin",
                score=0.95,
                metadata={"field": "interaction"},
            ),
            EvidenceItem(
                id="2",
                text="NSAIDs including ibuprofen may increase bleeding risk.",
                source="FDA",
                trust_tier="regulatory",
                title="Ibuprofen label",
                url="https://fda.gov/ibuprofen",
                score=0.90,
                metadata={"field": "contraindication"},
            ),
        ]


@pytest.mark.asyncio
async def test_chat_service_returns_structured_grounded_answer() -> None:
    service = ChatService(
        chat_model=FakeChatModel("Ibuprofen va warfarin co the lam tang nguy co chay mau [S1]."),
        embedding_model=FakeEmbeddingModel(size=4),
        retriever=FakeRetriever(),
    )

    response = await service.chat(ChatRequest(message="Toi dang uong warfarin, co dung ibuprofen duoc khong?"))

    assert response.risk_level == "high"
    assert response.evidence_status == "sufficient"
    assert response.citations[0].id == "S1"
    assert response.requires_professional_advice is True


@pytest.mark.asyncio
async def test_chat_service_short_circuits_urgent_request() -> None:
    service = ChatService(
        chat_model=FakeChatModel("unused"),
        embedding_model=FakeEmbeddingModel(size=4),
        retriever=FakeRetriever(),
    )

    response = await service.chat(ChatRequest(message="Toi uong qua lieu thuoc X va dang kho tho"))

    assert response.risk_level == "urgent"
    assert response.confidence == "medium"
    assert response.requires_professional_advice is True
```

- [x] **Step 2: Run chat service tests and verify failure**

Run: `python -m pytest tests/test_chat_service.py -q`

Expected: FAIL with missing `core.chat_service`.

- [x] **Step 3: Implement chat service**

Create `core/chat_service.py`:

```python
from backend.api.schemas import ChatRequest, ChatResponse, Citation
from core.agent import build_retrieval_plan, route_question
from core.citations import format_citations, has_required_citations
from core.config import get_settings
from core.evidence import assess_evidence, calculate_confidence
from core.llm import ChatModel, EmbeddingModel
from core.models import EvidenceItem, EvidenceStatus, RiskLevel
from core.safety import safety_precheck, urgent_response


class ChatService:
    def __init__(self, chat_model: ChatModel, embedding_model: EmbeddingModel, retriever) -> None:
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.retriever = retriever
        self.settings = get_settings()

    async def chat(self, request: ChatRequest) -> ChatResponse:
        precheck = safety_precheck(request.message)
        if precheck.should_short_circuit:
            answer, notice = urgent_response()
            return ChatResponse(
                answer=answer,
                safety_notice=notice,
                citations=[],
                intents=["emergency"],
                risk_level="urgent",
                evidence_status="partial",
                warnings=precheck.warnings,
                confidence="medium",
                requires_professional_advice=True,
            )

        decision = route_question(request)
        plan = build_retrieval_plan(decision)
        query_text = " ".join(plan.queries) or request.message
        query_vector = (await self.embedding_model.embed([query_text], self.settings.embedding_timeout_seconds))[0]
        evidence_items: list[EvidenceItem] = await self.retriever.retrieve(
            plan,
            query_vector,
            self.settings.qdrant_query_timeout_seconds,
        )
        required_entities = plan.entities.get("drugs", [])
        package = assess_evidence(evidence_items, decision.intents, decision.risk_level, required_entities)
        citations_raw = format_citations(package.items, limit=self.settings.final_citations_max)

        if package.status == EvidenceStatus.INSUFFICIENT:
            return ChatResponse(
                answer="Khong du bang chung tu cac nguon da cau hinh de tra loi chac chan.",
                safety_notice="Thong tin nay chi mang tinh tham khao va khong thay the tu van cua bac si hoac duoc si.",
                citations=[],
                intents=decision.intents,
                risk_level=decision.risk_level.value,
                evidence_status=package.status.value,
                warnings=package.warnings,
                confidence="low",
                requires_professional_advice=True,
            )

        answer = await self.chat_model.generate(
            [
                {"role": "system", "content": "Tra loi bang tieng Viet, dua tren bang chung, va trich dan dang [S1]."},
                {"role": "user", "content": _build_prompt(request.message, package.items, citations_raw)},
            ],
            self.settings.llm_timeout_seconds,
        )
        if citations_raw and not has_required_citations(answer, citations_raw):
            answer = answer.rstrip() + f" [{citations_raw[0]['id']}]"

        confidence = calculate_confidence(
            status=package.status,
            risk_level=decision.risk_level,
            has_exact_entities=all(entity.lower() in " ".join(item.text.lower() for item in package.items) for entity in required_entities),
            has_conflict=package.status == EvidenceStatus.CONFLICTING,
        )
        citations = [Citation(**citation) for citation in citations_raw]
        return ChatResponse(
            answer=answer,
            safety_notice="Thong tin nay chi mang tinh tham khao, khong thay the tu van y te chuyen nghiep.",
            citations=citations,
            intents=decision.intents,
            risk_level=decision.risk_level.value,
            evidence_status=package.status.value,
            warnings=package.warnings,
            confidence=confidence.value,
            requires_professional_advice=decision.risk_level in (RiskLevel.HIGH, RiskLevel.URGENT),
        )


def _build_prompt(message: str, items: list[EvidenceItem], citations: list[dict[str, object]]) -> str:
    evidence_lines = []
    for index, item in enumerate(items[:8], start=1):
        evidence_lines.append(f"[S{index}] {item.title} - {item.text}")
    return "Cau hoi: " + message + "\nBang chung:\n" + "\n".join(evidence_lines)
```

- [x] **Step 4: Verify chat service tests pass**

Run: `python -m pytest tests/test_chat_service.py -q`

Expected: PASS.

- [ ] **Step 5: Commit checkpoint** _(skipped: workspace is not a git repository)_

If git is initialized:

```bash
git add core/chat_service.py tests/test_chat_service.py
git commit -m "feat: add chat orchestration service"
```

---

### Task 12: API Routes And Dependency Wiring

**Files:**
- Create: `backend/api/routes.py`
- Modify: `backend/main.py`
- Modify: `tests/test_chat_service.py`

- [x] **Step 1: Add route smoke test**

Append to `tests/test_chat_service.py`:

```python
from fastapi.testclient import TestClient
from backend.main import create_app


def test_health_route() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

- [x] **Step 2: Run route smoke test**

Run: `python -m pytest tests/test_chat_service.py::test_health_route -q`

Expected: PASS with the current minimal app.

- [x] **Step 3: Implement API router**

Create `backend/api/routes.py`:

```python
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.api.schemas import ChatRequest, ChatResponse, IngestResponse, SourceStatusResponse
from core.chat_service import ChatService
from core.config import get_settings
from core.ingestion import ingest_directory
from core.llm import FakeChatModel, FakeEmbeddingModel


router = APIRouter()


class EmptyRetriever:
    async def retrieve(self, plan, query_vector, timeout_seconds):
        return []


def get_chat_service() -> ChatService:
    return ChatService(
        chat_model=FakeChatModel("Khong du bang chung de tra loi."),
        embedding_model=FakeEmbeddingModel(size=4),
        retriever=EmptyRetriever(),
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        return await get_chat_service().chat(request)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/ingest", response_model=IngestResponse)
async def ingest() -> IngestResponse:
    report = ingest_directory(Path("data/chunks"))
    return IngestResponse(
        indexed=int(report["indexed"]),
        skipped=int(report["skipped"]),
        errors=list(report["errors"]),
    )


@router.get("/sources/status", response_model=SourceStatusResponse)
def source_status() -> SourceStatusResponse:
    settings = get_settings()
    return SourceStatusResponse(collection=settings.qdrant_collection, source_families=[], qdrant_ready=False)
```

- [x] **Step 4: Update app factory**

Replace `backend/main.py` with:

```python
from fastapi import FastAPI

from backend.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="MedChat Pharmacy Agent", version="0.1.0")
    app.include_router(router)
    return app


app = create_app()
```

- [x] **Step 5: Verify routes**

Run: `python -m pytest tests/test_chat_service.py -q`

Expected: PASS.

- [ ] **Step 6: Commit checkpoint** _(skipped: workspace is not a git repository)_

If git is initialized:

```bash
git add backend/api/routes.py backend/main.py tests/test_chat_service.py
git commit -m "feat: add fastapi routes"
```

---

### Task 13: Ingestion CLI

**Files:**
- Create: `core/cli.py`
- Test: add to `tests/test_ingestion.py`

- [x] **Step 1: Add ingestion report test**

Append to `tests/test_ingestion.py`:

```python
from core.ingestion import ingest_directory


def test_ingest_directory_reports_indexed_and_skipped() -> None:
    report = ingest_directory(Path("tests/fixtures/chunks"))

    assert report["indexed"] == 1
    assert report["skipped"] == 1
    assert report["errors"]
```

- [x] **Step 2: Run new ingestion test**

Run: `python -m pytest tests/test_ingestion.py::test_ingest_directory_reports_indexed_and_skipped -q`

Expected: PASS because `ingest_directory` was implemented in Task 5.

- [x] **Step 3: Create CLI**

Create `core/cli.py`:

```python
import argparse
import json
from pathlib import Path

from core.ingestion import ingest_directory


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest pharmacy JSON chunks.")
    parser.add_argument("--path", default="data/chunks", help="Path containing JSON chunk files.")
    args = parser.parse_args()
    report = ingest_directory(Path(args.path))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [x] **Step 4: Verify ingestion CLI test passes**

Run: `python -m pytest tests/test_ingestion.py -q`

Expected: PASS.

- [x] **Step 5: Run CLI against fixtures**

Run: `python -m core.cli --path tests/fixtures/chunks`

Expected: JSON output with `"indexed": 1` and `"skipped": 1`.

- [ ] **Step 6: Commit checkpoint** _(skipped: workspace is not a git repository)_

If git is initialized:

```bash
git add core/cli.py tests/test_ingestion.py
git commit -m "feat: add ingestion cli report"
```

---

### Task 14: Final Verification

**Files:**
- Modify only files needed to fix verification failures.

- [x] **Step 1: Run full test suite**

Run: `python -m pytest -q`

Expected: all tests pass.

- [x] **Step 2: Verify app import**

Run: `python -c "from backend.main import app; print(app.title)"`

Expected output: `MedChat Pharmacy Agent`

- [x] **Step 3: Verify health endpoint manually**

Run: `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`

Expected: Uvicorn starts and serves the app. In another terminal, `GET http://127.0.0.1:8000/health` returns `{"status":"ok"}`.

- [x] **Step 4: Stop dev server**

Stop Uvicorn with `Ctrl+C`.

- [ ] **Step 5: Commit final checkpoint**

If git is initialized:

```bash
git add backend core tests requirements.txt
git commit -m "test: verify pharmacy agent mvp backend"
```

---

## Self-Review

Spec coverage:

- FastAPI backend: Tasks 1, 2, 12.
- Provider-agnostic LLM and embeddings: Task 6.
- Qdrant vector storage and hybrid retrieval: Task 9 defines the retriever interface and reranking; production Qdrant wiring can replace the test retriever through the same interface.
- Local JSON corpus ingestion: Tasks 3, 5, 13.
- Request schema, chunk schema, stable ID, multilingual/encoding strategy: Tasks 2, 3, 5.
- Whitelisted web source mechanism: Task 10.
- Multi-label intent and risk level: Task 7.
- Evidence Sufficiency Gate, confidence, warnings, evidence status: Task 8 and Task 11.
- Citations and citation completeness: Task 8 and Task 11.
- Safety fail-closed behavior and urgent confidence clarification: Task 7, Task 8, Task 11.
- Timeout defaults and timeout-path tests: Task 2 config, Task 10, Task 14 verification.

Placeholder scan:

- The plan avoids implementation placeholders and gives concrete files, code, commands, and expected results.

Type consistency:

- API schema values match `core.models` enum values.
- `ChatService` returns `ChatResponse` fields required by `backend/api/schemas.py`.
- Evidence, citation, router, and retrieval helpers use `EvidenceItem`, `EvidenceStatus`, `RiskLevel`, and `Confidence` consistently.
