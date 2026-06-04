"""Evidence Coverage Gate."""

from dataclasses import dataclass
import re

from core.models import EvidenceItem, EvidenceStatus, MergedEntities, RiskLevel
from core.text import accent_fold

ENTITY_TOKEN_STOPWORDS = {
    "thuoc",
    "nho",
    "mat",
    "dung",
    "dich",
    "vien",
    "siro",
    "chai",
    "hop",
    "duoc",
}


@dataclass
class EvidenceCoverage:
    status: EvidenceStatus
    per_facet_coverage: dict[str, str]
    gaps: list[str]
    warnings: list[str]

def assess_coverage(
    facet_results: dict[str, list[EvidenceItem]],
    merged_entities: MergedEntities,
    risk_level: RiskLevel,
    classification_uncertain: bool,
) -> EvidenceCoverage:
    gaps: list[str] = []
    warnings: list[str] = []
    per_facet_coverage: dict[str, str] = {}
    
    if not facet_results or not any(facet_results.values()):
        return EvidenceCoverage(
            status=EvidenceStatus.INSUFFICIENT,
            per_facet_coverage={},
            gaps=["No relevant evidence found."],
            warnings=["empty"],
        )

    all_items = [item for items in facet_results.values() for item in items]
    all_text = " ".join(_evidence_search_text(item) for item in all_items)
    folded_text = accent_fold(all_text)
    
    missing_required = [
        entity for entity in merged_entities.required 
        if not _entity_covered(entity, folded_text)
    ]
    
    if missing_required:
        gaps.append("Missing required entities: " + ", ".join(missing_required))
        warnings.append("missing_entities")

    missing_facets = 0
    partial_facets = 0
    total_required_facets = len(facet_results)
    
    for facet_id, items in facet_results.items():
        if not items:
            per_facet_coverage[facet_id] = "missing"
            missing_facets += 1
            gaps.append(f"Missing evidence for facet: {facet_id}")
        else:
            if len(items) < 2 and risk_level in {RiskLevel.HIGH, RiskLevel.URGENT}:
                per_facet_coverage[facet_id] = "partial"
                partial_facets += 1
                warnings.append(f"Narrow evidence for high-risk facet: {facet_id}")
            else:
                per_facet_coverage[facet_id] = "complete"

    has_conflict = any(
        "conflict" in folded_text or "mau thuan" in folded_text or "trai nguoc" in folded_text
        for items in facet_results.values()
    )

    status = EvidenceStatus.COMPLETE
    
    if has_conflict:
        status = EvidenceStatus.CONFLICTING
    elif missing_required:
        status = EvidenceStatus.INSUFFICIENT
    elif missing_facets == total_required_facets:
        status = EvidenceStatus.INSUFFICIENT
    elif missing_facets > 0 or partial_facets > 0:
        if risk_level in {RiskLevel.HIGH, RiskLevel.URGENT}:
            status = EvidenceStatus.WEAK_PARTIAL
        else:
            status = EvidenceStatus.USABLE_PARTIAL
            
    if classification_uncertain and status == EvidenceStatus.COMPLETE:
        status = EvidenceStatus.USABLE_PARTIAL
        warnings.append("classification_uncertain")

    return EvidenceCoverage(
        status=status,
        per_facet_coverage=per_facet_coverage,
        gaps=gaps,
        warnings=warnings
    )


def _evidence_search_text(item: EvidenceItem) -> str:
    metadata_name = item.metadata.get("name", "")
    return " ".join(str(part) for part in (item.title, metadata_name, item.text) if part)


def _entity_covered(entity: str, folded_text: str) -> bool:
    folded_entity = accent_fold(entity)
    if not folded_entity:
        return True
    if folded_entity in folded_text:
        return True

    tokens = [
        token
        for token in folded_entity.split()
        if _is_distinctive_entity_token(token)
    ]
    if not tokens:
        return False

    matches = sum(
        1
        for token in tokens
        if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", folded_text)
    )
    if len(tokens) == 1:
        return matches == 1
    if len(tokens) == 2:
        return matches == 2
    return matches >= 2


def _is_distinctive_entity_token(token: str) -> bool:
    return (
        len(token) >= 3
        and token not in ENTITY_TOKEN_STOPWORDS
        and not token.isdigit()
    )
