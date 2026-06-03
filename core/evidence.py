from core.models import Confidence, EvidenceItem, EvidencePackage, EvidenceStatus, RiskLevel
from core.text import accent_fold


INTENT_FIELD_COVERAGE = {
    "interaction": {"interaction", "tuong_tac_thuoc"},
    "contraindication": {"contraindication", "chong_chi_dinh", "warning", "canh_bao", "than_trong", "careful"},
    "dosage": {"dosage", "lieu_luong_va_cach_dung", "cach_dung"},
    "pregnancy_lactation": {"pregnancy_lactation", "phu_nu_co_thai_va_cho_con_bu", "careful"},
    "disease_context": {"disease_context", "overview", "describe", "cause", "causes", "symptom", "symptoms"},
    "symptom_triage": {"symptom_triage", "general_health", "overview", "describe", "cause", "symptoms"},
    "pediatric_elderly": {"pediatric_elderly", "dosage", "careful", "warning"},
    "indication": {"indication", "cong_dung", "chi_dinh", "describe"},
    "general_health": {"general_health", "general health", "overview", "describe"},
}


def assess_evidence(
    items: list[EvidenceItem],
    required_intents: list[str],
    risk_level: RiskLevel,
    required_entities: list[str],
) -> EvidencePackage:
    if not items:
        return EvidencePackage(
            [],
            EvidenceStatus.INSUFFICIENT,
            ["No relevant evidence found."],
            ["empty"],
        )

    warnings: list[str] = []
    reasons: list[str] = []
    fields = _evidence_fields(items)
    entity_text = accent_fold(" ".join(item.text for item in items))

    missing_entities = [
        entity for entity in required_entities if accent_fold(entity) not in entity_text
    ]
    if missing_entities:
        warnings.append("Evidence does not cover all named entities: " + ", ".join(missing_entities))
        reasons.append("missing_entities")

    missing_intents = [
        intent
        for intent in required_intents
        if not _intent_is_covered(intent, fields, entity_text, required_entities, missing_entities)
    ]
    if missing_intents:
        warnings.append("Evidence does not cover all requested intents: " + ", ".join(missing_intents))
        reasons.append("missing_intents")

    if risk_level == RiskLevel.HIGH:
        distinct_urls = {item.url or item.id for item in items}
        if len(distinct_urls) < 2:
            warnings.append("High-risk answer has fewer than two distinct evidence sources.")
            reasons.append("narrow_sources")

    if "missing_entities" in reasons:
        status = EvidenceStatus.INSUFFICIENT
    else:
        status = EvidenceStatus.PARTIAL if reasons else EvidenceStatus.SUFFICIENT
    return EvidencePackage(items, status, warnings, reasons)


def _intent_is_covered(
    intent: str,
    fields: set[str],
    entity_text: str,
    required_entities: list[str],
    missing_entities: list[str],
) -> bool:
    if intent == "drug_identity" and required_entities and not missing_entities:
        return True
    if intent == "drug_identity" and not missing_entities:
        return True
    accepted_fields = {_coverage_token(field) for field in INTENT_FIELD_COVERAGE.get(intent, set())}
    if accepted_fields and fields.intersection(accepted_fields):
        return True
    return _coverage_token(intent) in fields or intent in entity_text


def _evidence_fields(items: list[EvidenceItem]) -> set[str]:
    fields: set[str] = set()
    for item in items:
        raw_field = accent_fold(str(item.metadata.get("field", "")))
        for part in raw_field.replace("|", ",").replace(";", ",").split(","):
            field = _coverage_token(part)
            if field:
                fields.add(field)
    return fields


def _coverage_token(value: str) -> str:
    return accent_fold(value).replace("_", " ").strip()


def calculate_confidence(
    status: EvidenceStatus,
    risk_level: RiskLevel,
    has_exact_entities: bool,
    has_conflict: bool,
) -> Confidence:
    if has_conflict or status in {EvidenceStatus.INSUFFICIENT, EvidenceStatus.CONFLICTING}:
        return Confidence.LOW

    if risk_level == RiskLevel.URGENT:
        return Confidence.MEDIUM if status == EvidenceStatus.SUFFICIENT else Confidence.LOW

    if risk_level == RiskLevel.HIGH and status == EvidenceStatus.PARTIAL:
        return Confidence.LOW

    if (
        status == EvidenceStatus.SUFFICIENT
        and has_exact_entities
        and risk_level in {RiskLevel.LOW, RiskLevel.MEDIUM}
    ):
        return Confidence.HIGH

    if status in {EvidenceStatus.SUFFICIENT, EvidenceStatus.PARTIAL}:
        return Confidence.MEDIUM

    return Confidence.LOW
