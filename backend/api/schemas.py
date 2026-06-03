from typing import Literal
from pydantic import BaseModel, Field, field_validator


RiskLevel = Literal["low", "medium", "high", "urgent"]
EvidenceStatus = Literal["complete", "usable_partial", "weak_partial", "insufficient", "conflicting", "sufficient", "partial"]
Confidence = Literal["high", "medium", "low"]
Audience = Literal["general", "professional"]
PregnancyStatus = Literal["unknown", "not_pregnant", "pregnant", "planning_pregnancy"]
WebMode = Literal["trusted", "open"]


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
    force_web: bool = False
    qdrant_search: bool = True
    web_mode: WebMode = "trusted"
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
