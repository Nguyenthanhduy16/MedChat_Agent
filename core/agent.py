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

KNOWN_PRODUCTS = {
    "melatonin nature s bounty": "Melatonin Nature's Bounty",
    "melatonin nature's bounty": "Melatonin Nature's Bounty",
    "melatonin": "Melatonin",
    "men vi sinh": "men vi sinh",
}

KNOWN_DRUG_CLASSES = {
    "thuoc chong tram cam": "thuoc chong tram cam",
}

KNOWN_CONDITIONS = {
    "suy than": "suy than",
}

INTENT_ORDER = (
    "interaction",
    "contraindication",
    "overdose",
    "adverse_effect",
    "careful",
    "dosage",
    "pregnancy_lactation",
    "symptom_triage",
    "disease_context",
    "pediatric_elderly",
    "indication",
    "drug_identity",
    "general_health",
    "unsupported",
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
    "tieu chay",
    "mat ngu",
    "ngu",
    "men vi sinh",
    "tram cam",
    "khoc da de",
    "ung thu",
    "hoi chung",
    "roi loan",
    "di tat",
    "bam sinh",
    "chan",
    "tay",
    "da",
    "xuong",
    "khop",
    "tim",
    "gan",
    "than",
    "phoi",
    "nao",
)

SYMPTOM_TERMS = (
    "dau",
    "sung",
    "nhay cam",
    "nong",
    "te",
    "yeu",
    "ngua",
    "phat ban",
    "chay mau",
    "kho tho",
    "sot",
    "tieu chay",
    "khoc da de",
    "mat ngu",
)

BODY_PART_TERMS = (
    "phan tren cua ban chan",
    "mu ban chan",
    "ban chan",
    "chan",
    "co chan",
    "ngon chan",
    "got chan",
    "tay",
    "co tay",
    "ngon tay",
    "mat",
    "da",
    "nguc",
    "bung",
    "lung",
    "xuong",
    "khop",
)

CONDITION_PATTERNS = (
    r"\bung\s+thu(?:\s+\w+){0,3}",
    r"\bbenh\s+([\w\s]{2,80})",
    r"\b([\w\s]{2,80})\s+la\s+gi\b",
    r"\bthong\s+tin\s+ve\s+benh\s+([\w\s]{2,80})",
)

QUESTION_STOP_WORDS = {
    "co",
    "co nguy hiem khong",
    "nguy hiem khong",
    "khong",
    "la gi",
}


def _extract_drugs(message: str) -> list[str]:
    folded = accent_fold(message)
    drugs = [drug for drug in KNOWN_DRUGS if drug in folded]
    active_ingredient = _extract_active_ingredient(message)
    if active_ingredient:
        drugs.append(active_ingredient)
    named_product = _extract_named_drug_product(message)
    if named_product:
        drugs.append(named_product)
    return list(dict.fromkeys(drugs))


def _extract_taxonomy_terms(message: str, taxonomy: dict[str, str]) -> list[str]:
    folded = accent_fold(message)
    matches: list[str] = []
    for term, canonical in sorted(taxonomy.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", folded):
            if not any(term in accent_fold(match) for match in matches):
                matches.append(canonical)
    return matches


def _extract_clinical_qualifiers(message: str) -> list[str]:
    normalized = normalize_text(message)
    folded = accent_fold(message)
    qualifiers: list[str] = []
    clcr = re.search(r"\bclcr\s*(<)?\s*(\d+)\s*ml\s*phut\b", normalized, flags=re.IGNORECASE)
    if clcr:
        operator = " <" if clcr.group(1) else ""
        qualifiers.append(f"Clcr{operator} {clcr.group(2)} ml phut")
    age = re.search(r"\b\d+\s*thang\s*tuoi\b", folded)
    if age:
        qualifiers.append(age.group(0).replace("  ", " "))
    return qualifiers


def _extract_active_ingredient(message: str) -> str | None:
    normalized = normalize_text(message)
    match = re.search(
        r"(?:hoat\s+chat|hoạt\s+chất|duoc\s+chat|dược\s+chất|active\s+(?:ingredient|substance))"
        r"\s+([A-Za-z][A-Za-z0-9+-]*(?:\s+[A-Za-z][A-Za-z0-9+-]*){0,3})",
        normalized,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    ingredient = re.split(
        r"\s+(la|là|co|có|dung|dùng|de|để|tri|trị|chua|chữa|khong|không)\b",
        match.group(1),
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" ?.,")
    if len(ingredient) < 2:
        return None
    return ingredient


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
    products = _extract_taxonomy_terms(request.message, KNOWN_PRODUCTS)
    drug_classes = _extract_taxonomy_terms(request.message, KNOWN_DRUG_CLASSES)
    list_group = extract_list_group_term(request.message)
    if list_group and list_group not in drug_classes:
        drug_classes.append(list_group)
    known_conditions = _extract_taxonomy_terms(request.message, KNOWN_CONDITIONS)
    conditions = [
        condition
        for condition in _extract_conditions(request.message)
        if not _overlaps_known_condition(condition, known_conditions)
    ]
    conditions = list(dict.fromkeys(known_conditions + conditions))
    clinical_qualifiers = _extract_clinical_qualifiers(request.message)
    symptoms = _extract_terms(folded, SYMPTOM_TERMS)
    body_parts = _extract_terms(folded, BODY_PART_TERMS)
    medication_entities = drugs + products + drug_classes
    has_contraindication_request = any(term in folded for term in ("khong nen dung", "ai khong nen dung", "chong chi dinh"))

    if (
        any(term in folded for term in ("tuong tac", "uong chung", "dung chung", "dung them"))
        or len(drugs) >= 2
        or (products and drug_classes)
    ):
        intents.extend(["interaction", "contraindication"])
        risk = RiskLevel.HIGH
    if any(term in folded for term in ("qua lieu", "xu tri qua lieu")):
        intents.append("overdose")
        risk = RiskLevel.HIGH
    if any(term in folded for term in ("tac dung khong mong muon", "tac dung phu", "phan ung phu", "adr")):
        intents.append("adverse_effect")
        risk = max_risk(risk, RiskLevel.MEDIUM)
    if not has_contraindication_request and any(term in folded for term in ("luu y", "than trong", "canh bao", "an toan")):
        intents.append("careful")
        risk = max_risk(risk, RiskLevel.MEDIUM)
    if "overdose" not in intents and _contains_dosage_request(folded):
        intents.append("dosage")
        risk = max_risk(risk, RiskLevel.MEDIUM)
    if has_contraindication_request:
        intents.append("contraindication")
    if any(term in folded for term in ("mang thai", "cho con bu", "thai")):
        intents.append("pregnancy_lactation")
        risk = RiskLevel.HIGH
    if symptoms and (body_parts or "bi benh gi" in folded or "benh gi" in folded):
        intents.extend(["symptom_triage", "disease_context"])
    if conditions:
        intents.append("disease_context")
    if any(term in folded for term in ("tre em", "nguoi gia", "suy than")) or any("thang tuoi" in item for item in clinical_qualifiers):
        intents.append("pediatric_elderly" if "tre em" in folded or "nguoi gia" in folded or any("thang tuoi" in item for item in clinical_qualifiers) else "disease_context")
        risk = RiskLevel.HIGH
    if _contains_indication_request(folded) or is_list_group_request(folded):
        intents.append("indication")
    if products and any(term in folded for term in ("co nen dung", "uong nhu the nao", "dung nhu the nao")):
        if "dosage" not in intents and any(term in folded for term in ("uong", "dung")):
            intents.append("dosage")
    if not intents:
        if medication_entities:
            intents.append("drug_identity")
        elif _is_health_scope(folded):
            intents.append("general_health")
        else:
            intents.append("unsupported")

    deduped = _ordered_unique_intents(intents)
    return RouterDecision(
        intents=deduped,
        risk_level=risk,
        audience=request.preferences.audience,
        needs_context=risk == RiskLevel.HIGH,
        entities={
            "drugs": drugs,
            "products": products,
            "drug_classes": drug_classes,
            "ingredients": [],
            "conditions": conditions,
            "clinical_qualifiers": clinical_qualifiers,
            "symptoms": symptoms,
            "body_parts": body_parts,
        },
    )


def _ordered_unique_intents(intents: list[str]) -> list[str]:
    deduped = set(intents)
    return [intent for intent in INTENT_ORDER if intent in deduped]


def _overlaps_known_condition(condition: str, known_conditions: list[str]) -> bool:
    folded = accent_fold(condition)
    return any(accent_fold(known) in folded for known in known_conditions)


def _is_health_scope(folded_message: str) -> bool:
    return any(
        re.search(rf"(?<!\w){re.escape(term)}(?!\w)", folded_message)
        for term in HEALTH_SCOPE_TERMS
    )


def is_list_group_request(folded_message: str) -> bool:
    return (
        "liet ke" in folded_message
        and "nhom" in folded_message
        and any(term in folded_message for term in ("thuoc", "hoat chat", "duoc chat"))
    )


def extract_list_group_term(message: str) -> str | None:
    folded = accent_fold(message)
    if not is_list_group_request(folded):
        return None
    match = re.search(r"\bnhom\s+(.+?)(?:\s+trong\s+du\s+lieu|\s+trong\s+data|[?.!,]|$)", folded)
    if not match:
        return None
    group = match.group(1).strip(" ?.,")
    return group or None


def _contains_dosage_request(folded_message: str) -> bool:
    if any(
        term in folded_message
        for term in ("cach dung", "quen lieu", "uong nhu the nao", "dung nhu the nao", "lieu dung", "lieu luong")
    ):
        return True
    return re.search(r"(?<!du )\blieu\b", folded_message) is not None


def _contains_indication_request(folded_message: str) -> bool:
    if any(
        term in folded_message
        for term in ("dung de lam gi", "cong dung", "co nen dung", "ho tro khong")
    ):
        return True
    return re.search(r"(?<!chong )chi dinh", folded_message) is not None


def _extract_conditions(message: str) -> list[str]:
    normalized = normalize_text(message)
    folded = accent_fold(normalized)
    conditions: list[str] = []
    for pattern in CONDITION_PATTERNS:
        match = re.search(pattern, folded)
        if match:
            if match.lastindex:
                start, end = match.span(match.lastindex)
            else:
                start, end = match.span()
            condition = normalized[start:end]
            cleaned = _clean_condition_phrase(condition)
            if cleaned and _looks_like_condition(cleaned):
                conditions.append(cleaned)
    return list(dict.fromkeys(condition for condition in conditions if condition))


def _clean_condition_phrase(condition: str) -> str:
    cleaned = condition.strip(" ?.,")
    for stop_word in QUESTION_STOP_WORDS:
        cleaned = re.sub(rf"\s+{re.escape(stop_word)}$", "", cleaned, flags=re.IGNORECASE).strip(" ?.,")
    if len(cleaned) < 2:
        return ""
    return cleaned


def _looks_like_condition(condition: str) -> bool:
    folded = accent_fold(condition)
    return _is_health_scope(folded) or len(folded.split()) >= 2


def _extract_terms(folded_message: str, terms: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for term in sorted(terms, key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", folded_message):
            if " " not in term and any(term in match for match in matches):
                continue
            matches.append(term)
    return sorted(matches, key=terms.index)


def max_risk(left: RiskLevel, right: RiskLevel) -> RiskLevel:
    order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.URGENT]
    return order[max(order.index(left), order.index(right))]


def build_retrieval_plan(decision: RouterDecision) -> RetrievalPlan:
    fields: list[str] = []
    for intent in decision.intents:
        if intent == "interaction":
            fields.extend(["interaction", "warning"])
        elif intent == "contraindication":
            fields.extend(["contraindication", "warning", "careful"])
        elif intent == "overdose":
            fields.extend(["overdose", "xu_tri_qua_lieu", "qua_lieu_va_xu_tri"])
        elif intent == "adverse_effect":
            fields.extend(["adverse_effect", "side_effects", "tac_dung_phu"])
        elif intent == "careful":
            fields.extend(["careful", "warning", "than_trong", "canh_bao"])
        elif intent == "pregnancy_lactation":
            fields.extend(["pregnancy_lactation", "warning"])
        elif intent in {"dosage", "indication"}:
            fields.append(intent)
    query_entities = (
        decision.entities.get("drugs", [])
        + decision.entities.get("products", [])
        + decision.entities.get("drug_classes", [])
        + decision.entities.get("conditions", [])
        + decision.entities.get("clinical_qualifiers", [])
        + decision.entities.get("symptoms", [])
        + decision.entities.get("body_parts", [])
    )
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
