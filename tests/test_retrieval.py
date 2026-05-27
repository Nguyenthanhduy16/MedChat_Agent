from types import SimpleNamespace

import pytest
from qdrant_client.http.models import Fusion, FusionQuery, SparseVector

from core.models import RetrievalPlan, RiskLevel
from core.retrieval import QdrantRetriever, rerank_evidence
from core.models import EvidenceItem


@pytest.mark.asyncio
async def test_qdrant_retriever_applies_metadata_filters_with_field_aliases() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.query_filter = None
            self.prefetch = None
            self.query = None

        async def query_points(self, **kwargs):
            self.query_filter = kwargs["query_filter"]
            self.prefetch = kwargs["prefetch"]
            self.query = kwargs["query"]
            return SimpleNamespace(points=[])

    client = FakeClient()
    plan = RetrievalPlan(
        intents=["interaction"],
        risk_level=RiskLevel.HIGH,
        queries=["warfarin ibuprofen interaction"],
        entities={"drugs": ["warfarin", "ibuprofen"]},
        metadata_filters={
            "field": ["interaction"],
            "trust_tier": ["local_curated"],
        },
    )

    await QdrantRetriever(client, "pharmacy_chunks").retrieve(plan, [0.1, 0.2], timeout_seconds=5)

    conditions = client.query_filter.must
    assert len(client.prefetch) == 2
    assert client.prefetch[0].using == "dense"
    assert client.prefetch[0].query == [0.1, 0.2]
    assert client.prefetch[1].using == "sparse"
    assert isinstance(client.prefetch[1].query, SparseVector)
    assert client.prefetch[1].query.indices
    assert client.prefetch[1].query.values
    assert isinstance(client.query, FusionQuery)
    assert client.query.fusion == Fusion.RRF
    field_condition = next(condition for condition in conditions if condition.key == "field")
    trust_condition = next(condition for condition in conditions if condition.key == "trust_tier")
    assert set(field_condition.match.any) >= {"interaction", "tuong_tac_thuoc"}
    assert trust_condition.match.any == ["local_curated"]


@pytest.mark.asyncio
async def test_qdrant_retriever_falls_back_when_filter_index_is_missing() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        async def query_points(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs.get("query_filter") is not None:
                raise RuntimeError('Index required but not found for "field"')
            return SimpleNamespace(points=[])

    client = FakeClient()
    plan = RetrievalPlan(
        intents=["interaction"],
        risk_level=RiskLevel.HIGH,
        queries=["warfarin ibuprofen interaction"],
        entities={"drugs": ["warfarin", "ibuprofen"]},
        metadata_filters={"field": ["interaction"]},
    )

    items = await QdrantRetriever(client, "pharmacy_chunks").retrieve(plan, [0.1, 0.2], timeout_seconds=5)

    assert items == []
    assert client.calls[0]["query_filter"] is not None
    assert client.calls[1]["query_filter"] is None


def test_rerank_treats_vietnamese_field_alias_as_preferred() -> None:
    items = [
        EvidenceItem(
            "generic",
            "warfarin ibuprofen",
            "Long Chau",
            "local_curated",
            "Generic",
            None,
            0.80,
            {"sparse_score": 0.0, "field": "general"},
        ),
        EvidenceItem(
            "interaction",
            "warfarin ibuprofen",
            "Long Chau",
            "local_curated",
            "Interaction",
            None,
            0.70,
            {"sparse_score": 0.0, "field": "tuong_tac_thuoc"},
        ),
    ]

    ranked = rerank_evidence(items, preferred_fields=["interaction"], required_entities=[])

    assert ranked[0].id == "interaction"


@pytest.mark.asyncio
async def test_qdrant_retriever_uses_reranker_scores_to_reorder_candidates() -> None:
    class FakeClient:
        async def query_points(self, **kwargs):
            return SimpleNamespace(
                points=[
                    SimpleNamespace(
                        id="generic",
                        score=0.95,
                        payload={
                            "text": "Pain relief article with no warfarin detail.",
                            "source": "Blog",
                            "trust_tier": "web_whitelisted",
                            "name": "Generic",
                            "field": "general",
                        },
                    ),
                    SimpleNamespace(
                        id="specific",
                        score=0.80,
                        payload={
                            "text": "Warfarin and ibuprofen may increase bleeding risk.",
                            "source": "DailyMed",
                            "trust_tier": "regulatory",
                            "name": "Specific",
                            "field": "interaction",
                        },
                    ),
                ]
            )

    class FakeReranker:
        def __init__(self) -> None:
            self.calls = []

        async def score(self, query: str, passages: list[str], timeout_seconds: float) -> list[float]:
            self.calls.append((query, passages, timeout_seconds))
            return [0.99, 0.05]

    reranker = FakeReranker()
    plan = RetrievalPlan(
        intents=["interaction"],
        risk_level=RiskLevel.HIGH,
        queries=["warfarin ibuprofen interaction"],
        entities={"drugs": ["warfarin", "ibuprofen"]},
        metadata_filters={"field": ["interaction"]},
    )

    items = await QdrantRetriever(FakeClient(), "pharmacy_chunks", reranker=reranker).retrieve(
        plan,
        [0.1, 0.2],
        timeout_seconds=5,
    )

    assert items[0].id == "specific"
    assert reranker.calls
    assert items[0].metadata["reranker_score"] == 0.99
