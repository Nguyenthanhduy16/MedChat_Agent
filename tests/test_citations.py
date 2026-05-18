from core.citations import format_citations, has_required_citations
from core.models import EvidenceItem


def test_format_citations_dedupes_urls_and_assigns_ids() -> None:
    items = [
        EvidenceItem("1", "A", "DailyMed", "regulatory", "Warfarin", "https://x.test/a", 0.9),
        EvidenceItem("2", "B", "DailyMed", "regulatory", "Warfarin duplicate", "https://x.test/a", 0.8),
    ]

    citations = format_citations(items)

    assert len(citations) == 1
    assert citations[0]["id"] == "S1"
    assert citations[0]["url"] == "https://x.test/a"


def test_has_required_citations_detects_missing_marker() -> None:
    assert has_required_citations("Claim [S1].", [{"id": "S1"}]) is True
    assert has_required_citations("Claim without marker.", [{"id": "S1"}]) is False
