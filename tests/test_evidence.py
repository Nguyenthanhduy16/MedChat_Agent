from core.evidence import assess_evidence, calculate_confidence
from core.models import EvidenceItem, EvidenceStatus, RiskLevel
from core.retrieval import rerank_evidence


def test_evidence_item_defaults() -> None:
    item = EvidenceItem(
        id="chunk-1",
        text="Warfarin interacts with NSAIDs.",
        source="DailyMed",
        trust_tier="regulatory",
        title="Warfarin label",
        url="https://dailymed.nlm.nih.gov/example",
        score=0.91,
        metadata={"field": "interaction"},
    )

    assert item.source == "DailyMed"
    assert item.metadata["field"] == "interaction"


def test_evidence_item_metadata_defaults_are_independent() -> None:
    first = EvidenceItem(
        id="chunk-1",
        text="Warfarin interacts with NSAIDs.",
        source="DailyMed",
        trust_tier="regulatory",
        title="Warfarin label",
        url="https://dailymed.nlm.nih.gov/example",
        score=0.91,
    )
    second = EvidenceItem(
        id="chunk-2",
        text="NSAIDs may increase bleeding risk.",
        source="FDA",
        trust_tier="regulatory",
        title="Ibuprofen label",
        url="https://fda.gov/example",
        score=0.88,
    )

    first.metadata["field"] = "interaction"

    assert second.metadata == {}


def test_evidence_gate_marks_high_risk_single_source_as_partial() -> None:
    item = EvidenceItem(
        id="S1",
        text="Warfarin and ibuprofen may increase bleeding risk.",
        source="DailyMed",
        trust_tier="regulatory",
        title="Warfarin",
        url="https://dailymed.nlm.nih.gov/warfarin",
        score=0.95,
        metadata={"field": "interaction", "entities": ["warfarin", "ibuprofen"]},
    )

    package = assess_evidence(
        items=[item],
        required_intents=["interaction", "contraindication"],
        risk_level=RiskLevel.HIGH,
        required_entities=["warfarin", "ibuprofen"],
    )

    assert package.status == EvidenceStatus.PARTIAL
    assert package.warnings


def test_confidence_never_high_for_urgent_personal_scenario() -> None:
    confidence = calculate_confidence(
        status=EvidenceStatus.SUFFICIENT,
        risk_level=RiskLevel.URGENT,
        has_exact_entities=True,
        has_conflict=False,
    )

    assert confidence.value == "medium"


def test_rerank_combines_dense_sparse_metadata_and_trust() -> None:
    items = [
        EvidenceItem(
            "a",
            "generic pain text",
            "Blog",
            "web_whitelisted",
            "A",
            "https://a.test",
            0.90,
            {"sparse_score": 0.1, "field": "general"},
        ),
        EvidenceItem(
            "b",
            "warfarin ibuprofen bleeding",
            "DailyMed",
            "regulatory",
            "B",
            "https://b.test",
            0.80,
            {"sparse_score": 1.0, "field": "interaction"},
        ),
    ]

    ranked = rerank_evidence(items, preferred_fields=["interaction"], required_entities=["warfarin", "ibuprofen"])

    assert ranked[0].id == "b"
