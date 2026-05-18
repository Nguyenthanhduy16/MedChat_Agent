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


@dataclass
class RetrievalPlan:
    intents: list[str]
    risk_level: RiskLevel
    queries: list[str]
    entities: dict[str, list[str]]
    metadata_filters: dict[str, list[str]]
