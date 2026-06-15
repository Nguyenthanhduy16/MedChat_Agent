from core.models import EvidenceItem


def format_citations(
    items: list[EvidenceItem], limit: int = 8
) -> list[dict[str, str | None]]:
    citations: list[dict[str, str | None]] = []
    seen_keys: set[str] = set()

    for item in sorted(items, key=lambda evidence: evidence.score, reverse=True):
        dedupe_key = item.url if item.url else item.id
        if dedupe_key in seen_keys:
            continue

        seen_keys.add(dedupe_key)
        citations.append(
            {
                "id": f"{len(citations) + 1}",
                "doc_id": dedupe_key,
                "title": item.title,
                "url": item.url,
                "source": item.source,
                "trust_tier": item.trust_tier,
                "snippet": item.text[:300],
                "text": item.text,
            }
        )

        if len(citations) >= limit:
            break

    return citations


def has_required_citations(answer: str, citations: list[dict[str, object]]) -> bool:
    if not citations:
        return False

    return any(f"[{citation.get('id')}]" in answer for citation in citations)
