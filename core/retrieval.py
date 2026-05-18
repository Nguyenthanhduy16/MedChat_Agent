from qdrant_client import AsyncQdrantClient

from core.models import EvidenceItem, RetrievalPlan
from core.text import accent_fold


TRUST_WEIGHT = {
    "regulatory": 0.30,
    "clinical_reference": 0.20,
    "local_curated": 0.15,
    "web_whitelisted": 0.05,
}


def rerank_evidence(
    items: list[EvidenceItem],
    preferred_fields: list[str],
    required_entities: list[str],
) -> list[EvidenceItem]:
    def combined(item: EvidenceItem) -> float:
        text_folded = accent_fold(item.text)
        sparse = float(item.metadata.get("sparse_score", 0.0))
        field_bonus = 0.15 if item.metadata.get("field") in preferred_fields else 0.0
        entity_bonus = 0.0
        if required_entities:
            matches = sum(1 for entity in required_entities if accent_fold(entity) in text_folded)
            entity_bonus = 0.25 * (matches / len(required_entities))
        trust_bonus = TRUST_WEIGHT.get(item.trust_tier, 0.0)
        return item.score + sparse + field_bonus + entity_bonus + trust_bonus

    return sorted(items, key=combined, reverse=True)


class QdrantRetriever:
    def __init__(self, client: AsyncQdrantClient, collection: str) -> None:
        self.client = client
        self.collection = collection

    async def retrieve(self, plan: RetrievalPlan, query_vector: list[float], timeout_seconds: float) -> list[EvidenceItem]:
        response = await self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=20,
            with_payload=True,
            timeout=int(timeout_seconds) if timeout_seconds else None,
        )
        results = response.points
        items: list[EvidenceItem] = []
        for point in results:
            payload = point.payload or {}
            text = str(payload.get("text", ""))
            sparse_score = _sparse_score(text, plan.queries + plan.entities.get("drugs", []))
            metadata = dict(payload)
            metadata["sparse_score"] = sparse_score
            items.append(
                EvidenceItem(
                    id=str(point.id),
                    text=text,
                    source=str(payload.get("source", "unknown")),
                    trust_tier=str(payload.get("trust_tier", "local_curated")),
                    title=str(payload.get("name", payload.get("title", "Untitled"))),
                    url=payload.get("url"),
                    score=float(point.score),
                    metadata=metadata,
                )
            )
        return rerank_evidence(
            items,
            preferred_fields=plan.metadata_filters.get("field", []),
            required_entities=plan.entities.get("drugs", []),
        )


def _sparse_score(text: str, terms: list[str]) -> float:
    folded = accent_fold(text)
    if not terms:
        return 0.0
    matches = sum(1 for term in terms if accent_fold(term) in folded)
    return matches / len(terms)
