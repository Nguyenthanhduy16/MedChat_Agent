from types import SimpleNamespace

import pytest

from core.models import RetrievalPlan, RiskLevel
from core.retrieval import QdrantRetriever, rerank_evidence
from core.models import EvidenceItem


@pytest.mark.asyncio
async def test_qdrant_retriever_applies_metadata_filters_with_field_aliases() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.query_filter = None

        async def query_points(self, **kwargs):
            self.query_filter = kwargs["query_filter"]
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
