"""Answer Synthesizer."""

from core.models import EvidenceItem, EvidenceStatus
from core.query_planner import QueryFacet
from core.evidence_gate import EvidenceCoverage


def _has_web_evidence(facet_evidence: dict[str, list[EvidenceItem]]) -> bool:
    """Return True if any evidence item comes from a web source."""
    return any(
        item.trust_tier == "web_whitelisted" or (item.id or "").startswith("web:")
        for items in facet_evidence.values()
        for item in items
    )

def build_prompt(
    original_question: str,
    facets: list[QueryFacet],
    facet_evidence: dict[str, list[EvidenceItem]],
    coverage: EvidenceCoverage,
    citations: list[dict[str, str | None]],
) -> list[dict[str, str]]:
    
    item_to_citation = {c.get("doc_id", ""): c["id"] for c in citations}
    evidence_blocks: list[str] = []
    
    for facet in facets:
        items = facet_evidence.get(facet.intent, [])
        if not items:
            continue
            
        block = f"--- Evidence for: {facet.intent} ---\n"
        for item in items:
            dedupe_key = item.url if item.url else item.id
            marker = item_to_citation.get(dedupe_key)
            if not marker:
                continue
            is_web = item.trust_tier == "web_whitelisted" or (item.id or "").startswith("web:")
            source_tag = "[WEB]" if is_web else "[LOCAL]"
            block += f"[{marker}]{source_tag} {item.title} ({item.source}, {item.trust_tier}): {item.text}\n"

        evidence_blocks.append(block)

    has_web = _has_web_evidence(facet_evidence)
    web_notice = (
        "\n- IMPORTANT: Some evidence is tagged [WEB]. "
        "For any claim sourced from [WEB] evidence, you MUST add a clear disclosure in Vietnamese "
        "at the end of that sentence or paragraph, for example: "
        "'(Thông tin này được tổng hợp từ nguồn trên Internet, chưa được kiểm chứng lâm sàng.)'"
        "\n- Clearly separate web-sourced information from local database information in your answer."
    ) if has_web else ""

    system = (
        "You are a pharmacy safety assistant. Answer in Vietnamese, be concise, "
        "use only the supplied evidence, cite claims with source markers like [1], "
        "and advise professional care for high-risk medication questions.\n\n"
        "RULES FOR CITATIONS:\n"
        "- Do not make medical claims without citing the evidence [#].\n"
        "- If combining facts, cite both [1][2].\n"
        f"{web_notice}"
    )
    
    if coverage.status == EvidenceStatus.COMPLETE:
        system += "- You have complete evidence. Provide a clear, well-supported conclusion.\n"
    elif coverage.status == EvidenceStatus.USABLE_PARTIAL:
        system += (
            "- You have partial evidence. Answer the part you have evidence for.\n"
            "- EXPLICITLY state what information is missing or not found in your sources.\n"
        )
    elif coverage.status == EvidenceStatus.WEAK_PARTIAL:
        system += (
            "- You have weak/insufficient evidence for high-risk queries.\n"
            "- DO NOT provide specific dosages or definitive safety clearances.\n"
            "- Provide general safety guidance and recommend consulting a doctor/pharmacist.\n"
            "- State clearly that you lack sufficient data.\n"
        )
    elif coverage.status == EvidenceStatus.INSUFFICIENT:
        system += (
            "- You DO NOT have enough evidence to answer safely.\n"
            "- State that you lack sufficient information.\n"
            "- Ask the user to provide more details or consult a healthcare professional.\n"
        )
    elif coverage.status == EvidenceStatus.CONFLICTING:
        system += (
            "- The evidence contains conflicting information.\n"
            "- Present both sides of the conflict clearly.\n"
            "- DO NOT draw a definitive conclusion. Recommend consulting a doctor.\n"
        )

    if coverage.gaps:
        system += f"\nKnown Gaps in Evidence:\n- {chr(10).join(coverage.gaps)}\n"

    evidence_text = "\n\n".join(evidence_blocks) if evidence_blocks else "No cited evidence."
    user = f"Question: {original_question}\n\nEvidence:\n{evidence_text}"

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
