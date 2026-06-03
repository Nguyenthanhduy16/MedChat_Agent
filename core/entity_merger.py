"""Entity Merger: Combines entities from multiple sources."""

from core.models import MergedEntities, ResolvedEntity
from core.text import accent_fold

def merge_entities(
    resolved_entities: list[ResolvedEntity],
    fallback_entities: dict[str, list[str]],
) -> MergedEntities:
    required: list[str] = []
    optional: list[str] = []
    candidates: list[str] = []
    
    seen_canonical = set()
    
    for entity in sorted(resolved_entities, key=lambda e: e.confidence, reverse=True):
        if entity.canonical in seen_canonical:
            continue
            
        seen_canonical.add(entity.canonical)
        
        if entity.confidence >= 0.8:
            required.append(entity.canonical)
        elif entity.confidence >= 0.5:
            optional.append(entity.canonical)
        else:
            candidates.append(entity.canonical)
            
    for category, values in fallback_entities.items():
        for val in values:
            canonical_val = accent_fold(val)
            if canonical_val not in seen_canonical:
                seen_canonical.add(canonical_val)
                optional.append(canonical_val)
                    
    return MergedEntities(
        required=required,
        optional=optional,
        candidates=candidates
    )
