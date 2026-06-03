"""Answer Synthesizer."""

from core.models import EvidenceItem, EvidenceStatus
from core.query_planner import QueryFacet
from core.evidence_gate import EvidenceCoverage

def build_prompt(
    original_question: str,
    facets: list[QueryFacet],
    facet_evidence: dict[str, list[EvidenceItem]],
    coverage: EvidenceCoverage,
    citations: list[dict[str, str | None]],
) -> list[dict[str, str]]:
    
    citation_lookup = {str(c["id"]): c for c in citations}
    evidence_blocks: list[str] = []
    
    for facet in facets:
        items = facet_evidence.get(facet.intent, [])
        if not items:
            continue
            
        block = f"--- Evidence for: {facet.intent} ---\n"
        for index, item in enumerate(items, start=1):
            marker = f"S{index}"
            if marker not in citation_lookup:
                continue
            block += f"[{marker}] {item.title} ({item.source}, {item.trust_tier}): {item.text}\n"
            
        evidence_blocks.append(block)

    system = (
        "You are a pharmacy safety assistant. Answer in Vietnamese, be concise, "
        "use only the supplied evidence, cite claims with source markers like [S1], "
        "and advise professional care for high-risk medication questions.\n\n"
        "RULES FOR CITAIONS:\n"
        "- Do not make medical claims without citing the evidence [S#].\n"
        "- If combining facts, cite both [S1][S2].\n"
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
