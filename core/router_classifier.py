"""LLM Router Classifier using schemas."""

import json
import logging
from typing import Literal

from backend.api.schemas import ChatRequest
from core.agent import extract_list_group_term, is_list_group_request
from core.models import RouterDecision, RiskLevel
from core.input_normalizer import NormalizedInput
from core.llm import ChatModel
from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)


AllowedIntent = Literal[
    "dosage",
    "interaction",
    "contraindication",
    "overdose",
    "adverse_effect",
    "careful",
    "pregnancy_lactation",
    "disease_context",
    "symptom_triage",
    "pediatric_elderly",
    "indication",
    "drug_identity",
    "general_health",
    "unsupported",
]

RouterAudience = Literal["adult", "pediatric", "elderly", "general", "professional"]


class RouterEntitiesPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    drugs: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    drug_classes: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    clinical_qualifiers: list[str] = Field(default_factory=list)
    body_parts: list[str] = Field(default_factory=list)


class RouterClassifierPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    intents: list[AllowedIntent] = Field(min_length=1)
    risk_level: RiskLevel
    audience: RouterAudience
    needs_context: bool
    entities: RouterEntitiesPayload
    confidence: float = Field(ge=0.0, le=1.0)


class LLMRouterClassifier:
    def __init__(self, chat_model: ChatModel, confidence_threshold: float = 0.6) -> None:
        self.chat_model = chat_model
        self.confidence_threshold = confidence_threshold

    async def classify(
        self,
        request: ChatRequest,
        normalized: NormalizedInput,
        fallback_decision: RouterDecision,
        timeout_seconds: float,
    ) -> RouterDecision:
        try:
            messages = self._build_router_prompt(request, normalized)
            raw = await self.chat_model.generate(messages, timeout_seconds=timeout_seconds)
            json_str = self._extract_json_object(raw)
            payload = json.loads(json_str)
            validated = RouterClassifierPayload.model_validate(payload)
            
            if validated.confidence < self.confidence_threshold:
                logger.warning(
                    "router.llm fallback reason=low_confidence confidence=%s threshold=%s",
                    validated.confidence,
                    self.confidence_threshold,
                )
                return self._fallback(fallback_decision)
            
            decision = RouterDecision(
                intents=list(validated.intents),
                risk_level=validated.risk_level,
                audience=validated.audience,
                needs_context=validated.needs_context,
                entities=validated.entities.model_dump(),
                classification_uncertain=False,
            )
            return self._normalize_decision(request, normalized, decision)
        except ValidationError as exc:
            logger.warning("router.llm fallback reason=schema_validation_failed errors=%s", exc.errors())
            return self._fallback(fallback_decision)
        except Exception as exc:
            logger.warning("router.llm fallback reason=%s", exc)
            return self._fallback(fallback_decision)

    def _fallback(self, fallback_decision: RouterDecision) -> RouterDecision:
        fallback_decision.classification_uncertain = True
        return fallback_decision

    def _extract_json_object(self, raw: str) -> str:
        text = raw.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            return text
        return text[start : end + 1]

    def _normalize_decision(
        self,
        request: ChatRequest,
        normalized: NormalizedInput,
        decision: RouterDecision,
    ) -> RouterDecision:
        if not is_list_group_request(normalized.normalized):
            return decision

        decision.intents = ["indication"]
        decision.risk_level = RiskLevel.LOW
        decision.needs_context = False
        group = extract_list_group_term(request.message)
        if group:
            classes = decision.entities.setdefault("drug_classes", [])
            if group not in classes:
                classes.append(group)
        return decision

    def _build_router_prompt(self, request: ChatRequest, normalized: NormalizedInput) -> list[dict[str, str]]:
        system = (
            "You are a medical router. Analyze the user query and return ONLY a JSON object matching this schema:\n"
            "{\n"
            "  \"intents\": [\"dosage\", \"interaction\", \"contraindication\", \"overdose\", \"adverse_effect\", \"careful\", \"pregnancy_lactation\", \"disease_context\", \"symptom_triage\", \"pediatric_elderly\", \"indication\", \"drug_identity\", \"general_health\", \"unsupported\"],\n"
            "  \"risk_level\": \"low\" | \"medium\" | \"high\" | \"urgent\",\n"
            "  \"audience\": \"adult\" | \"pediatric\" | \"elderly\",\n"
            "  \"needs_context\": boolean,\n"
            "  \"entities\": {\"drugs\": [], \"products\": [], \"drug_classes\": [], \"conditions\": [], \"symptoms\": [], \"clinical_qualifiers\": [], \"body_parts\": []},\n"
            "  \"confidence\": float\n"
            "}\n"
            "IMPORTANT INSTRUCTIONS:\n"
            "1. Extract entities EXACTLY as they appear in the original user query. DO NOT translate them to English. Keep them in Vietnamese.\n"
            "2. If the query is completely unrelated to pharmacy, medicine, health, or diseases (e.g., math, programming, general chit-chat), you MUST return [\"unsupported\"] for intents.\n"
            "3. For Vietnamese list/discovery queries like 'liệt kê một số thuốc/hoạt chất thuộc nhóm ...', use intent [\"indication\"] and put the group after 'nhóm' in entities.drug_classes.\n"
            "Be precise. Do not add explanations."
        )
        user = f"Question: {normalized.original}\nAudience preference: {request.preferences.audience}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
