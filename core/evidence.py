from core.models import Confidence, EvidenceItem, EvidencePackage, EvidenceStatus, RiskLevel


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
    fields = {str(item.metadata.get("field", "")) for item in items}
    entity_text = " ".join(item.text for item in items).lower()

    missing_entities = [
        entity for entity in required_entities if entity.lower() not in entity_text
    ]
    if missing_entities:
        warnings.append("Evidence does not cover all named entities: " + ", ".join(missing_entities))
        reasons.append("missing_entities")

    missing_intents = [
        intent
        for intent in required_intents
        if intent not in fields and intent not in entity_text
    ]
    if missing_intents:
        warnings.append("Evidence does not cover all requested intents: " + ", ".join(missing_intents))
        reasons.append("missing_intents")

    if risk_level == RiskLevel.HIGH:
        distinct_urls = {item.url or item.id for item in items}
        if len(distinct_urls) < 2:
            warnings.append("High-risk answer has fewer than two distinct evidence sources.")
            reasons.append("narrow_sources")

    status = EvidenceStatus.PARTIAL if reasons else EvidenceStatus.SUFFICIENT
    return EvidencePackage(items, status, warnings, reasons)


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

    if (
        status == EvidenceStatus.SUFFICIENT
        and has_exact_entities
        and risk_level in {RiskLevel.LOW, RiskLevel.MEDIUM}
    ):
        return Confidence.HIGH

    if status in {EvidenceStatus.SUFFICIENT, EvidenceStatus.PARTIAL}:
        return Confidence.MEDIUM

    return Confidence.LOW
