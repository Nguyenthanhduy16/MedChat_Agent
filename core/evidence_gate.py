"""Evidence Coverage Gate."""

from dataclasses import dataclass
import re

from core.models import EvidenceItem, EvidenceStatus, MergedEntities, RiskLevel
from core.text import accent_fold

STOP_PHRASES = [
    "thuoc nho mat", "thuoc nho mui", "thuoc boi", "thuoc uong", "thuoc tiem", "thuoc xit", 
    "thuoc", "vien nen", "vien nang", "vien sui", "dung dich", "hon dich", "siro", 
    "tuyp", "chai", "hop", "vi", "ong", "tpcn", "thuc pham chuc nang"
]
STOP_PHRASE_PATTERN = re.compile(r"\b(" + "|".join(STOP_PHRASES) + r")\b", flags=re.IGNORECASE)

ENTITY_TOKEN_STOP_PATTERNS = (
    re.compile(r"^\d+(?:\.\d+)?(?:mg|mcg|g|kg|ml|l|iu|ui|%)$"),
    re.compile(r"^\d+x\d+$"),
    re.compile(r"^\d+(?:v|vien|goi|ong|lo|chai|hop)$"),
    re.compile(r"^(?:mg|mcg|g|kg|ml|l|iu|ui)$"),
)


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
            warnings=[],
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
        warnings.append("Chủ đề của câu hỏi không hoàn toàn rõ ràng, câu trả lời có thể chỉ mang tính tương đối.")

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

    # Loai bo cac cum tu rac truoc khi tach tu
    cleaned_entity = STOP_PHRASE_PATTERN.sub(" ", folded_entity)

    tokens = [
        token
        for token in cleaned_entity.split()
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
    # Cho phep giu lai cac token ngan (C, A, B1) hoac so (500)
    # chi bo qua cac ky tu don le khong phai chu/so
    if len(token) == 1 and not token.isalnum():
        return False
    # Bo qua cac token la lieu luong/nong do de evidence gate khong bi reject oan
    if any(pattern.match(token) for pattern in ENTITY_TOKEN_STOP_PATTERNS):
        return False
    return True


def filter_evidence_by_entities_and_fields(
    facet_results: dict[str, list["EvidenceItem"]],
    required_entities: list[str],
    facet_preferred_fields: dict[str, list[str]],
) -> dict[str, list["EvidenceItem"]]:
    """Filter retrieved evidence to keep only items relevant to the correct entity and field.

    For each facet:
    - Entity filter: the item’s title/text must mention at least one required entity.
    - Field filter (soft): if the facet has preferred fields, prefer items whose
      ``metadata['field']`` is in that list; items without a matching field are
      deprioritised but not discarded if filtering would leave the facet empty.

    Fallback strategy (per facet):
    1. entity + field match  → use
    2. entity match only     → use if (1) is empty
    3. original items        → use if (2) is empty (prevent total evidence loss)
    """
    if not required_entities and not facet_preferred_fields:
        return facet_results

    folded_entities = [
        accent_fold(e).lower().strip()
        for e in required_entities
        if e and e.strip()
    ]

    filtered: dict[str, list["EvidenceItem"]] = {}

    for facet_id, items in facet_results.items():
        preferred_fields = set(facet_preferred_fields.get(facet_id, []))

        entity_field_pass: list["EvidenceItem"] = []
        entity_only_pass: list["EvidenceItem"] = []

        for item in items:
            search_text = accent_fold(_evidence_search_text(item)).lower()

            # --- entity gate ---
            if folded_entities:
                entity_hit = any(ent in search_text for ent in folded_entities)
            else:
                entity_hit = True  # no entity constraint → always passes

            if not entity_hit:
                continue  # discard item that doesn’t mention any required entity

            entity_only_pass.append(item)

            # --- field gate (soft) ---
            if preferred_fields:
                item_field = item.metadata.get("field", "")
                if item_field in preferred_fields:
                    entity_field_pass.append(item)
            else:
                entity_field_pass.append(item)  # no field constraint

        # Choose best non-empty tier
        if entity_field_pass:
            filtered[facet_id] = entity_field_pass
        elif entity_only_pass:
            filtered[facet_id] = entity_only_pass
        else:
            # All items were filtered out – fall back to original to avoid
            # incorrectly blocking a facet when entity matching is too strict.
            filtered[facet_id] = items

    return filtered
