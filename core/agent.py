import re

from backend.api.schemas import ChatRequest
from core.models import RetrievalPlan, RiskLevel, RouterDecision
from core.text import accent_fold, normalize_text


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

HEALTH_SCOPE_TERMS = (
    "dau",
    "sot",
    "ho",
    "kho tho",
    "benh",
    "trieu chung",
    "suc khoe",
    "thuoc",
    "duoc",
    "uong",
    "dung",
    "dieu tri",
    "di ung",
    "nhiem",
    "viem",
    "thai",
    "cho con bu",
    "tre em",
    "nguoi gia",
    "suy than",
    "ung thu",
)

CONDITION_PATTERNS = (
    r"\bung\s+thu(?:\s+\w+){0,3}",
)


def _extract_drugs(message: str) -> list[str]:
    folded = accent_fold(message)
    drugs = [drug for drug in KNOWN_DRUGS if drug in folded]
    named_product = _extract_named_drug_product(message)
    if named_product:
        drugs.append(named_product)
    return list(dict.fromkeys(drugs))


def _extract_named_drug_product(message: str) -> str | None:
    normalized = normalize_text(message)
    folded = accent_fold(normalized)
    if not folded.startswith("thuoc "):
        return None

    product = re.sub(r"^\s*(thuốc|thuoc)\s+", "", normalized, flags=re.IGNORECASE).strip()
    product = re.split(
        r"\s+(la|là|co|có|dung|dùng|de|để|tri|trị|chua|chữa|khong|không)\b",
        product,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" ?.,")
    if len(product) < 2:
        return None
    return product


def route_question(request: ChatRequest) -> RouterDecision:
    folded = accent_fold(request.message)
    intents: list[str] = []
    risk = RiskLevel.LOW
    drugs = _extract_drugs(request.message)
    conditions = _extract_conditions(request.message)

    if any(term in folded for term in ("tuong tac", "uong chung", "dung chung")) or len(drugs) >= 2:
        intents.extend(["interaction", "contraindication"])
        risk = RiskLevel.HIGH
    if any(term in folded for term in ("lieu", "cach dung", "qua lieu", "quen lieu")):
        intents.append("dosage")
        risk = RiskLevel.HIGH if "qua lieu" in folded else max_risk(risk, RiskLevel.MEDIUM)
    if any(term in folded for term in ("mang thai", "cho con bu", "thai")):
        intents.append("pregnancy_lactation")
        risk = RiskLevel.HIGH
    if conditions:
        intents.append("disease_context")
    if any(term in folded for term in ("tre em", "nguoi gia", "suy than")):
        intents.append("pediatric_elderly" if "tre em" in folded or "nguoi gia" in folded else "disease_context")
        risk = RiskLevel.HIGH
    if any(term in folded for term in ("dung de lam gi", "cong dung", "chi dinh")):
        intents.append("indication")
    if not intents:
        if drugs:
            intents.append("drug_identity")
        elif _is_health_scope(folded):
            intents.append("general_health")
        else:
            intents.append("unsupported")

    deduped = list(dict.fromkeys(intents))
    return RouterDecision(
        intents=deduped,
        risk_level=risk,
        audience=request.preferences.audience,
        needs_context=risk == RiskLevel.HIGH,
        entities={"drugs": drugs, "ingredients": [], "conditions": conditions},
    )


def _is_health_scope(folded_message: str) -> bool:
    return any(term in folded_message for term in HEALTH_SCOPE_TERMS)


def _extract_conditions(message: str) -> list[str]:
    normalized = normalize_text(message)
    folded = accent_fold(normalized)
    conditions: list[str] = []
    for pattern in CONDITION_PATTERNS:
        match = re.search(pattern, folded)
        if match:
            start, end = match.span()
            conditions.append(normalized[start:end].strip(" ?.,"))
    return list(dict.fromkeys(condition for condition in conditions if condition))


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
        elif intent in {"dosage", "indication"}:
            fields.append(intent)
    query_entities = decision.entities.get("drugs", []) + decision.entities.get("conditions", [])
    query = " ".join(query_entities + decision.intents)
    metadata_filters = {
        "trust_tier": ["regulatory", "clinical_reference", "local_curated"],
    }
    if fields:
        metadata_filters["field"] = list(dict.fromkeys(fields))

    return RetrievalPlan(
        intents=decision.intents,
        risk_level=decision.risk_level,
        queries=[query.strip()],
        entities=decision.entities,
        metadata_filters=metadata_filters,
    )
