import logging

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import FieldCondition, Filter, Fusion, FusionQuery, MatchAny, Prefetch

from core.models import EvidenceItem, RetrievalPlan
from core.sparse_vectors import build_sparse_vector
from core.text import accent_fold
from core.config import get_settings


logger = logging.getLogger(__name__)


FIELD_ALIASES = {
    "interaction": ["interaction", "tuong_tac_thuoc"],
    "contraindication": ["contraindication", "chong_chi_dinh", "careful"],
    "warning": ["warning", "canh_bao", "than_trong", "careful"],
    "careful": ["careful", "warning", "canh_bao", "than_trong"],
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
        reranker = float(item.metadata.get("reranker_score", 0.0))
        field_bonus = 0.15 if item.metadata.get("field") in expanded_preferred_fields else 0.0
        entity_bonus = 0.0
        if required_entities:
            matches = sum(1 for entity in required_entities if accent_fold(entity) in text_folded)
            entity_bonus = 0.25 * (matches / len(required_entities))
        trust_bonus = TRUST_WEIGHT.get(item.trust_tier, 0.0)
        return item.score + sparse + reranker + field_bonus + entity_bonus + trust_bonus

    return sorted(items, key=combined, reverse=True)


class QdrantRetriever:
    def __init__(
        self,
        client: AsyncQdrantClient,
        collection: str,
        reranker=None,
        reranker_top_k: int = 10,
        reranker_timeout_seconds: float = 10.0,
    ) -> None:
        self.client = client
        self.collection = collection
        self.reranker = reranker
        self.reranker_top_k = reranker_top_k
        self.reranker_timeout_seconds = reranker_timeout_seconds

    async def retrieve(self, plan: RetrievalPlan, query_vector: list[float], timeout_seconds: float) -> list[EvidenceItem]:
        query_filter = _build_query_filter(plan.metadata_filters)
        logger.info(
            "retrieval.qdrant start collection=%s intents=%s filters=%s vector_size=%s",
            self.collection,
            plan.intents,
            plan.metadata_filters,
            len(query_vector),
        )
        response = await self._query_points(
            plan=plan,
            query_vector=query_vector,
            query_filter=query_filter,
            timeout_seconds=timeout_seconds,
        )
        results = response.points
        logger.info("retrieval.qdrant raw_count=%s", len(results))
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
        ranked = rerank_evidence(
            items,
            preferred_fields=plan.metadata_filters.get("field", []),
            required_entities=plan.entities.get("drugs", []),
        )
        reranked = await self._apply_reranker(plan, ranked)
        settings = get_settings()
        top_k = settings.local_top_k_per_intent
        final_ranked = reranked[:top_k]
        logger.info(
            "retrieval.qdrant ranked_count=%s returned_count=%s top=%s",
            len(reranked),
            len(final_ranked),
            [
                {
                    "title": item.title,
                    "score": item.score,
                    "field": item.metadata.get("field"),
                    "sparse_score": item.metadata.get("sparse_score"),
                    "reranker_score": item.metadata.get("reranker_score"),
                }
                for item in final_ranked[:3]
            ],
        )
        return final_ranked

    async def _query_points(
        self,
        plan: RetrievalPlan,
        query_vector: list[float],
        query_filter: Filter | None,
        timeout_seconds: float,
    ):
        sparse_query = build_sparse_vector(" ".join(_query_terms(plan)))
        try:
            return await self.client.query_points(
                collection_name=self.collection,
                prefetch=_hybrid_prefetch(query_vector, sparse_query),
                query=FusionQuery(fusion=Fusion.RRF),
                query_filter=query_filter,
                limit=20,
                with_payload=True,
                timeout=int(timeout_seconds) if timeout_seconds else None,
            )
        except Exception as exc:
            if query_filter is None or "Index required" not in str(exc):
                raise
            logger.warning("retrieval.qdrant filter_index_missing fallback_without_filter error=%s", exc)

        return await self.client.query_points(
            collection_name=self.collection,
            prefetch=_hybrid_prefetch(query_vector, sparse_query),
            query=FusionQuery(fusion=Fusion.RRF),
            query_filter=None,
            limit=20,
            with_payload=True,
            timeout=int(timeout_seconds) if timeout_seconds else None,
        )

    async def _apply_reranker(self, plan: RetrievalPlan, items: list[EvidenceItem]) -> list[EvidenceItem]:
        if self.reranker is None or not items:
            return items

        candidates = items[: self.reranker_top_k]
        query_text = " ".join(_query_terms(plan))
        passages = [item.text for item in candidates]
        try:
            scores = await self.reranker.score(
                query_text,
                passages,
                timeout_seconds=self.reranker_timeout_seconds,
            )
        except (TimeoutError, Exception) as exc:
            logger.warning("retrieval.reranker skipped (fallback to base ranking): %s", exc)
            return items

        for item, score in zip(candidates, scores, strict=True):
            item.metadata["reranker_score"] = float(score)
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


def _hybrid_prefetch(query_vector: list[float], sparse_query) -> list[Prefetch]:
    return [
        Prefetch(query=query_vector, using="dense", limit=20),
        Prefetch(query=sparse_query, using="sparse", limit=20),
    ]


def _query_terms(plan: RetrievalPlan) -> list[str]:
    terms = list(plan.queries)
    for entity_values in plan.entities.values():
        terms.extend(entity_values)
    return [term for term in terms if term]
