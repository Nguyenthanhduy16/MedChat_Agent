from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EvidenceStatus(str, Enum):
    # 5-state gate theo flow.md
    COMPLETE = "complete"              # đủ bằng chứng đầy đủ
    USABLE_PARTIAL = "usable_partial"  # trả lời phần có bằng chứng, nêu phần thiếu
    WEAK_PARTIAL = "weak_partial"      # chỉ định hướng an toàn, không kết luận/liều
    INSUFFICIENT = "insufficient"      # block LLM, hướng dẫn cần thêm thông tin
    CONFLICTING = "conflicting"        # nêu mâu thuẫn, không kết luận

    # Backward-compat aliases cho code cũ chưa migrate
    SUFFICIENT = "complete"
    PARTIAL = "usable_partial"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# ---------------------------------------------------------------------------
# Input normalization
# ---------------------------------------------------------------------------

@dataclass
class NormalizedInput:
    original: str
    normalized: str           # accent_fold output để matching/retrieval
    language: str             # "vi" | "en" | "mixed"
    question_parts: list[str] # câu hỏi nhiều phần nếu tách được


# ---------------------------------------------------------------------------
# Entity resolution & merging
# ---------------------------------------------------------------------------

@dataclass
class ResolvedEntity:
    text: str            # raw text từ câu hỏi
    canonical: str       # tên chuẩn từ corpus/KNOWN_*
    type: str            # "drug" | "product" | "drug_class" | "condition" | "clinical_qualifier"
    confidence: float    # 0.0–1.0
    source: str          # "corpus_exact" | "corpus_alias" | "llm" | "rule" | "pattern"


@dataclass
class MergedEntities:
    required: list[str]    # phải có trong evidence để answer
    optional: list[str]    # nên có nhưng không block
    candidates: list[str]  # chưa chắc, không dùng để gate


# ---------------------------------------------------------------------------
# Core retrieval models
# ---------------------------------------------------------------------------

@dataclass
class CanonicalChunk:
    id: str
    text: str
    sparse_text: str
    entities: dict[str, list[str]]
    metadata: dict[str, Any]


@dataclass
class EvidenceItem:
    id: str
    text: str
    source: str
    trust_tier: str
    title: str
    url: str | None
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    facet_id: str | None = None  # facet tạo ra item này, dùng để per-facet coverage


@dataclass
class EvidencePackage:
    items: list[EvidenceItem]
    status: EvidenceStatus
    warnings: list[str]
    reasons: list[str]


@dataclass
class RouterDecision:
    intents: list[str]
    risk_level: RiskLevel
    audience: str
    needs_context: bool
    entities: dict[str, list[str]]
    classification_uncertain: bool = False  # True nếu LLM confidence thấp


@dataclass
class RetrievalPlan:
    intents: list[str]
    risk_level: RiskLevel
    queries: list[str]
    entities: dict[str, list[str]]
    metadata_filters: dict[str, list[str]]
