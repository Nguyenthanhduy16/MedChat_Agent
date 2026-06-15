"""Answer Synthesizer."""

from core.models import EvidenceItem, EvidenceStatus, RouterDecision, RiskLevel
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
    main_entity: str,
    decision: RouterDecision,
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

    # Build Dynamic Sections
    def _has_evidence(intent: str) -> bool:
        return bool(facet_evidence.get(intent))
    
    sections = []
    if "overdose" in decision.intents and _has_evidence("overdose"):
        sections.append("Xử trí quá liều:\n[Trình bày chi tiết dựa vào tài liệu]")
    if "dosage" in decision.intents and _has_evidence("dosage"):
        sections.append("Liều dùng / cách dùng:\n[Trình bày chi tiết dựa vào tài liệu]")
    if "careful" in decision.intents and _has_evidence("careful"):
        sections.append("Lưu ý an toàn / thận trọng:\n[Trình bày chi tiết dựa vào tài liệu]")
    if "contraindication" in decision.intents and _has_evidence("contraindication"):
        sections.append("Chống chỉ định:\n[Trình bày chi tiết dựa vào tài liệu]")
    if "interaction" in decision.intents and _has_evidence("interaction"):
        sections.append("Tương tác thuốc:\n[Trình bày chi tiết dựa vào tài liệu]")
    if "pregnancy_lactation" in decision.intents and _has_evidence("pregnancy_lactation"):
        sections.append("Phụ nữ có thai / cho con bú:\n[Trình bày chi tiết dựa vào tài liệu]")
    if "adverse_effect" in decision.intents and _has_evidence("adverse_effect"):
        sections.append("Tác dụng phụ:\n[Trình bày chi tiết dựa vào tài liệu]")
    if "side_effect" in decision.intents and _has_evidence("side_effect"):
        sections.append("Tác dụng phụ:\n[Trình bày chi tiết dựa vào tài liệu]")
    if "disease_context" in decision.intents and _has_evidence("disease_context"):
        sections.append("Thông tin bệnh:\n[Trình bày chi tiết dựa vào tài liệu]")
    if "symptom_triage" in decision.intents and _has_evidence("symptom_triage"):
        sections.append("Định hướng xử trí:\n[Trình bày chi tiết dựa vào tài liệu]")
    if "general_health" in decision.intents and _has_evidence("general_health"):
        sections.append("Thông tin liên quan:\n[Trình bày chi tiết dựa vào tài liệu]")
    if "drug_identity" in decision.intents and _has_evidence("drug_identity"):
        sections.append("Thông tin thuốc:\n[Trình bày chi tiết dựa vào tài liệu]")
    if "indication" in decision.intents and _has_evidence("indication"):
        sections.append("Công dụng / chỉ định:\n[Trình bày chi tiết dựa vào tài liệu]")
        
    # Doctor advice section
    if decision.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.URGENT) and any(facet_evidence.values()):
        sections.append("Khi nào cần bác sĩ theo dõi:\n[Trình bày chi tiết dựa vào tài liệu]")

    # Missing evidence check
    missing_intents = [intent for intent in decision.intents if not _has_evidence(intent)]
    if missing_intents:
        sections.append("Thông tin chưa đủ:\n(Nói ngắn gọn: Tài liệu hiện có chưa đủ thông tin về...)")
        
    dynamic_format_sections = "\n\n".join(sections)
    
    # Dynamic intro & outro
    needs_doctor_warning = (
        decision.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.URGENT) or
        any(i in decision.intents for i in ["dosage", "interaction", "pregnancy_lactation", "careful"])
    )
    
    is_drug_query = any(i in decision.intents for i in ["dosage", "interaction", "pregnancy_lactation", "careful", "indication", "adverse_effect", "drug_identity", "overdose"])
    
    if needs_doctor_warning:
        if is_drug_query:
            drug_name = f"Với {main_entity}, n" if main_entity and main_entity != "thuốc" else "N"
            intro_rule = f"{drug_name}gười bệnh không nên tự ý sử dụng thuốc này nếu chưa có chỉ định của bác sĩ."
        else:
            intro_rule = "Người bệnh cần tham khảo ý kiến bác sĩ để được chẩn đoán và điều trị chính xác."
    else:
        intro_rule = "Trả lời trực tiếp vào vấn đề được hỏi."
    outro_rule = "\n\nLưu ý: Thông tin trên chỉ mang tính tham khảo và cần được bác sĩ/dược sĩ xác nhận trước khi sử dụng." if needs_doctor_warning else ""

    system = (
        "You are a pharmacy safety assistant. Answer in Vietnamese.\n\n"
        "CRITICAL RULES:\n"
        "1. Be extremely concise and direct. DO NOT use conversational filler like 'Chào bạn', 'Dưới đây là', 'Tôi là trợ lý'. Answer the question immediately.\n"
        "2. You MUST use ONLY the supplied evidence to answer. DO NOT add external medical knowledge or facts.\n"
        f"3. Only answer about the main entity: {main_entity}. Do not use information about other active ingredients/drugs.\n"
        "4. Do not output any section if it is not related to the user's intents.\n"
        "5. Do not output any section if there is no supporting evidence in the context.\n"
        "6. Do not output empty headings.\n"
        "7. For every important group of information, you MUST attach the corresponding citation [#]. If combining facts, cite both [1][2].\n"
        "8. Do NOT provide diagnosis or instructions for self-medication.\n\n"
        "RESPONSE FORMAT (Follow exactly):\n"
        f"{intro_rule}\n\n"
        f"{dynamic_format_sections}"
        f"{outro_rule}\n\n"
        f"{web_notice}"
    )
    
    if coverage.status == EvidenceStatus.COMPLETE:
        system += "- You have complete evidence. Provide a clear, well-supported conclusion.\n"
    elif coverage.status == EvidenceStatus.USABLE_PARTIAL:
        system += (
            "- You have partial evidence. Answer the part you have evidence for.\n"
            "- EXPLICITLY state what information is missing or not found in your sources.\n"
            "- WARNING: You MUST include a short disclaimer at the end: '*Lưu ý: Dữ liệu hạn chế.*'\n"
        )
    elif coverage.status == EvidenceStatus.WEAK_PARTIAL:
        system += (
            "- You have weak/insufficient evidence for high-risk queries.\n"
            "- DO NOT provide specific dosages or definitive safety clearances.\n"
            "- Provide general safety guidance.\n"
            "- State clearly that you lack sufficient data.\n"
            "- WARNING: You MUST include a short disclaimer at the end: '*Lưu ý: Dữ liệu hạn chế, vui lòng tham khảo bác sĩ.*'\n"
        )
    elif coverage.status == EvidenceStatus.INSUFFICIENT:
        system += (
            "- You DO NOT have enough evidence to answer safely.\n"
            "- State that you lack sufficient information by stating 'Tôi không tìm thấy thông tin này trong tài liệu hiện có'.\n"
            "- WARNING: You MUST include a short disclaimer at the end: '*Lưu ý: Vui lòng tham khảo bác sĩ.*'\n"
        )
    elif coverage.status == EvidenceStatus.CONFLICTING:
        system += (
            "- The evidence contains conflicting information.\n"
            "- Present both sides of the conflict clearly.\n"
            "- DO NOT draw a definitive conclusion. WARNING: You MUST include a short disclaimer at the end: '*Lưu ý: Vui lòng tham khảo bác sĩ.*'\n"
        )

    if coverage.gaps:
        system += f"\nKnown Gaps in Evidence:\n- {chr(10).join(coverage.gaps)}\n"

    evidence_text = "\n\n".join(evidence_blocks) if evidence_blocks else "No cited evidence."
    user = f"Question: {original_question}\n\nEvidence:\n{evidence_text}"

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
