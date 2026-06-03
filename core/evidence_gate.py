"""Evidence Coverage Gate."""

from dataclasses import dataclass
from core.models import EvidenceItem, EvidenceStatus, MergedEntities, RiskLevel
from core.text import accent_fold

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

    all_text = " ".join(
        item.text for items in facet_results.values() for item in items
    )
    folded_text = accent_fold(all_text)
    
    missing_required = [
        entity for entity in merged_entities.required 
        if accent_fold(entity) not in folded_text
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
