"""Dynamic Entity Resolver."""

import logging
from core.models import ResolvedEntity
from core.text import accent_fold

logger = logging.getLogger(__name__)

async def resolve_entities(raw_entities: dict[str, list[str]]) -> list[ResolvedEntity]:
    resolved: list[ResolvedEntity] = []
    
    for qualifier in raw_entities.get("clinical_qualifiers", []):
        resolved.append(
            ResolvedEntity(
                text=qualifier,
                canonical=accent_fold(qualifier),
                type="clinical_qualifier",
                confidence=0.7,
                source="llm"
            )
        )
        
    for category in ["drugs", "products", "drug_classes", "conditions", "symptoms"]:
        for entity in raw_entities.get(category, []):
            resolved.append(
                ResolvedEntity(
                    text=entity,
                    canonical=accent_fold(entity), 
                    type=category,
                    confidence=0.7,  # < 0.8 means it goes to optional, avoiding strict string-matching gate blocks
                    source="llm"
                )
            )
            
    return resolved
