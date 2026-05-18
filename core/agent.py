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
