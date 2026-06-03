"""LLM Router Classifier using schemas."""

import json
import logging

from backend.api.schemas import ChatRequest
from core.models import RouterDecision, RiskLevel
from core.input_normalizer import NormalizedInput
from core.llm import ChatModel

logger = logging.getLogger(__name__)

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
            
            is_uncertain = payload.get("confidence", 0.5) < self.confidence_threshold
            
            return RouterDecision(
                intents=payload.get("intents", fallback_decision.intents),
                risk_level=RiskLevel(payload.get("risk_level", fallback_decision.risk_level.value)),
                audience=payload.get("audience", fallback_decision.audience),
                needs_context=payload.get("needs_context", False),
                entities=payload.get("entities", fallback_decision.entities),
                classification_uncertain=is_uncertain,
            )
        except Exception as exc:
            logger.warning("router.llm fallback reason=%s", exc)
            fallback_decision.classification_uncertain = True
            return fallback_decision

    def _extract_json_object(self, raw: str) -> str:
        text = raw.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            return text
        return text[start : end + 1]

    def _build_router_prompt(self, request: ChatRequest, normalized: NormalizedInput) -> list[dict[str, str]]:
        system = (
            "You are a medical router. Analyze the user query and return ONLY a JSON object matching this schema:\n"
            "{\n"
            "  \"intents\": [\"dosage\", \"interaction\", \"contraindication\", \"pregnancy_lactation\", \"disease_context\", \"symptom_triage\", \"pediatric_elderly\", \"indication\", \"drug_identity\", \"general_health\", \"unsupported\"],\n"
            "  \"risk_level\": \"low\" | \"medium\" | \"high\" | \"urgent\",\n"
            "  \"audience\": \"adult\" | \"pediatric\" | \"elderly\",\n"
            "  \"needs_context\": boolean,\n"
            "  \"entities\": {\"drugs\": [], \"products\": [], \"drug_classes\": [], \"conditions\": [], \"symptoms\": [], \"clinical_qualifiers\": [], \"body_parts\": []},\n"
            "  \"confidence\": float\n"
            "}\n"
            "IMPORTANT: Extract entities EXACTLY as they appear in the original user query. DO NOT translate them to English. Keep them in Vietnamese.\n"
            "Be precise. Do not add explanations."
        )
        user = f"Question: {normalized.original}\nAudience preference: {request.preferences.audience}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
