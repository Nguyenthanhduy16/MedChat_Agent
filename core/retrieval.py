from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchAny

from core.models import EvidenceItem, RetrievalPlan
from core.text import accent_fold


FIELD_ALIASES = {
    "interaction": ["interaction", "tuong_tac_thuoc"],
    "contraindication": ["contraindication", "chong_chi_dinh"],
    "warning": ["warning", "canh_bao", "than_trong"],
    "dosage": ["dosage", "lieu_luong_va_cach_dung", "cach_dung"],
    "pregnancy_lactation": ["pregnancy_lactation", "phu_nu_co_thai_va_cho_con_bu"],
    "indication": ["indication", "cong_dung", "chi_dinh"],
    "overdose": ["overdose", "qua_lieu_va_xu_tri"],
}

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
    expanded_preferred_fields = set(_expand_field_values(preferred_fields))

    def combined(item: EvidenceItem) -> float:
        text_folded = accent_fold(item.text)
        sparse = float(item.metadata.get("sparse_score", 0.0))
        field_bonus = 0.15 if item.metadata.get("field") in expanded_preferred_fields else 0.0
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
        query_filter = _build_query_filter(plan.metadata_filters)
        response = await self._query_points(
            query_vector=query_vector,
            query_filter=query_filter,
            timeout_seconds=timeout_seconds,
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

    async def _query_points(self, query_vector: list[float], query_filter: Filter | None, timeout_seconds: float):
        try:
            return await self.client.query_points(
                collection_name=self.collection,
                query=query_vector,
                query_filter=query_filter,
                limit=20,
                with_payload=True,
                timeout=int(timeout_seconds) if timeout_seconds else None,
            )
        except Exception as exc:
            if query_filter is None or "Index required" not in str(exc):
                raise

        return await self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            query_filter=None,
            limit=20,
            with_payload=True,
            timeout=int(timeout_seconds) if timeout_seconds else None,
        )


def _sparse_score(text: str, terms: list[str]) -> float:
    folded = accent_fold(text)
    if not terms:
        return 0.0
    matches = sum(1 for term in terms if accent_fold(term) in folded)
    return matches / len(terms)


def _build_query_filter(metadata_filters: dict[str, list[str]]) -> Filter | None:
    conditions: list[FieldCondition] = []
    for key, values in metadata_filters.items():
        expanded_values = _expand_field_values(values) if key == "field" else values
        unique_values = list(dict.fromkeys(value for value in expanded_values if value))
        if unique_values:
            conditions.append(FieldCondition(key=key, match=MatchAny(any=unique_values)))
    if not conditions:
        return None
    return Filter(must=conditions)


def _expand_field_values(fields: list[str]) -> list[str]:
    expanded: list[str] = []
    for field in fields:
        expanded.extend(FIELD_ALIASES.get(field, [field]))
    return list(dict.fromkeys(expanded))
