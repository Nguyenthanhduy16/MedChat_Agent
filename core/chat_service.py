import logging

from backend.api.schemas import ChatRequest, ChatResponse, Citation
from core.agent import build_retrieval_plan, route_question
from core.citations import format_citations, has_required_citations
from core.config import get_settings
from core.evidence import assess_evidence, calculate_confidence
from core.llm import ChatModel, EmbeddingModel
from core.models import EvidenceItem, EvidencePackage, EvidenceStatus, RetrievalPlan, RiskLevel
from core.safety import safety_precheck, urgent_response
from core.web_sources import WebFetchedSource


logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        chat_model: ChatModel,
        embedding_model: EmbeddingModel,
        retriever,
        web_client=None,
    ) -> None:
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.retriever = retriever
        self.web_client = web_client
        self.settings = get_settings()

    async def chat(self, request: ChatRequest) -> ChatResponse:
        logger.info(
            "chat.start message_len=%s allow_web=%s force_web=%s qdrant_search=%s web_mode=%s",
            len(request.message),
            request.retrieval_options.allow_web,
            request.retrieval_options.force_web,
            request.retrieval_options.qdrant_search,
            request.retrieval_options.web_mode,
        )
        precheck = safety_precheck(request.message)
        logger.info(
            "chat.safety should_short_circuit=%s risk=%s warnings=%s",
            precheck.should_short_circuit,
            precheck.risk_level.value,
            precheck.warnings,
        )
        if precheck.should_short_circuit:
            answer, notice = urgent_response()
            return ChatResponse(
                answer=answer,
                safety_notice=notice,
                citations=[],
                intents=["emergency"],
                risk_level=RiskLevel.URGENT.value,
                evidence_status=EvidenceStatus.PARTIAL.value,
                warnings=precheck.warnings,
                confidence="medium",
                requires_professional_advice=True,
            )

        decision = route_question(request)
        logger.info(
            "chat.route intents=%s risk=%s entities=%s needs_context=%s",
            decision.intents,
            decision.risk_level.value,
            decision.entities,
            decision.needs_context,
        )
        if "unsupported" in decision.intents:
            logger.info("chat.unsupported reason=outside_scope")
            return ChatResponse(
                answer=(
                    "Câu hỏi này nằm ngoài phạm vi dược/y tế của hệ thống, "
                    "nên tôi không có nguồn phù hợp để trả lời."
                ),
                safety_notice="Hệ thống chỉ cung cấp thông tin tham khảo trong phạm vi dược và y tế.",
                citations=[],
                intents=decision.intents,
                risk_level=decision.risk_level.value,
                evidence_status=EvidenceStatus.INSUFFICIENT.value,
                warnings=["Question is outside the configured pharmacy and health scope."],
                confidence="low",
                requires_professional_advice=False,
            )

        plan = build_retrieval_plan(decision)
        retrieval_plan = _broad_retrieval_plan(plan)
        query_text = _build_hybrid_query(request.message, plan)
        logger.info(
            "chat.retrieval_plan query=%r filters=%s broad_filters=%s",
            query_text,
            plan.metadata_filters,
            retrieval_plan.metadata_filters,
        )
        query_vectors = await self.embedding_model.embed(
            [query_text],
            timeout_seconds=self.settings.embedding_timeout_seconds,
        )
        logger.info("chat.embedding vector_size=%s", len(query_vectors[0]) if query_vectors else 0)
        if request.retrieval_options.qdrant_search:
            items = await self.retriever.retrieve(
                retrieval_plan,
                query_vectors[0],
                timeout_seconds=self.settings.qdrant_query_timeout_seconds,
            )
        else:
            logger.info("chat.local_retrieval skipped reason=qdrant_search_disabled")
            items = []
        logger.info(
            "chat.local_retrieval count=%s top_titles=%s",
            len(items),
            [item.title for item in items[:3]],
        )

        required_entities = decision.entities.get("drugs", []) + decision.entities.get("conditions", [])
        evidence = assess_evidence(
            items,
            decision.intents,
            decision.risk_level,
            required_entities,
        )
        logger.info(
            "chat.evidence local_status=%s reasons=%s warnings=%s item_count=%s",
            evidence.status.value,
            evidence.reasons,
            evidence.warnings,
            len(evidence.items),
        )
        should_try_web, web_reason = _should_try_web(request, evidence, self.web_client)
        web_warnings: list[str] = []
        if should_try_web:
            logger.info("chat.web_retrieval start query=%r reason=%s", query_text, web_reason)
            try:
                web_sources = await self.web_client.retrieve(
                    retrieval_plan,
                    query_text=query_text,
                    timeout_seconds=self.settings.web_fetch_timeout_seconds,
                    max_sources=min(
                        request.retrieval_options.max_sources,
                        self.settings.max_web_urls_per_request,
                    ),
                    web_mode=request.retrieval_options.web_mode,
                )
            except Exception as exc:
                web_sources = []
                web_warnings.append(f"Web evidence retrieval failed: {exc}")
                logger.warning("chat.web_retrieval failed error=%s", exc)

            if web_sources:
                logger.info("chat.web_retrieval count=%s", len(web_sources))
                items = items + _web_sources_to_evidence_items(web_sources, retrieval_plan)
                evidence = assess_evidence(
                    items,
                    decision.intents,
                    decision.risk_level,
                    _web_required_entities(request, required_entities),
                )
                logger.info(
                    "chat.evidence combined_status=%s reasons=%s warnings=%s item_count=%s",
                    evidence.status.value,
                    evidence.reasons,
                    evidence.warnings,
                    len(evidence.items),
                )
            else:
                logger.info("chat.web_retrieval count=0")
        else:
            logger.info("chat.web_retrieval skipped reason=%s", web_reason)

        if web_warnings:
            evidence = EvidencePackage(
                items=evidence.items,
                status=evidence.status,
                warnings=evidence.warnings + web_warnings,
                reasons=evidence.reasons,
            )
        citations = format_citations(
            evidence.items,
            limit=self.settings.final_citations_max,
        )
        logger.info("chat.citations count=%s ids=%s", len(citations), [citation["id"] for citation in citations])

        if evidence.status == EvidenceStatus.INSUFFICIENT:
            logger.info("chat.finish insufficient")
            return ChatResponse(
                answer=(
                    "Toi chua co du bang chung dang tin cay de tra loi cau hoi nay. "
                    "Vui long hoi duoc si, bac si hoac cung cap them thong tin ve thuoc va tinh trang suc khoe."
                ),
                safety_notice="Thong tin nay khong thay the tu van truc tiep cua nhan vien y te.",
                citations=[],
                intents=decision.intents,
                risk_level=decision.risk_level.value,
                evidence_status=evidence.status.value,
                warnings=evidence.warnings,
                confidence="low",
                requires_professional_advice=decision.risk_level in {RiskLevel.HIGH, RiskLevel.URGENT},
            )

        messages = _build_prompt(request.message, evidence.items, citations)
        logger.info("chat.llm start evidence_count=%s citation_count=%s", len(evidence.items), len(citations))
        answer = await self.chat_model.generate(
            messages,
            timeout_seconds=self.settings.llm_timeout_seconds,
        )
        if citations and not has_required_citations(answer, citations):
            answer = f"{answer.rstrip()} [{citations[0]['id']}]"

        item_text = " ".join(item.text for item in evidence.items).lower()
        has_exact_entities = all(entity.lower() in item_text for entity in required_entities)
        has_conflict = _has_conflict(evidence.items) or evidence.status == EvidenceStatus.CONFLICTING
        confidence = calculate_confidence(
            evidence.status,
            decision.risk_level,
            has_exact_entities,
            has_conflict,
        )
        logger.info(
            "chat.finish status=%s confidence=%s risk=%s",
            evidence.status.value,
            confidence.value,
            decision.risk_level.value,
        )

        return ChatResponse(
            answer=answer,
            safety_notice="Thong tin nay khong thay the tu van truc tiep cua nhan vien y te.",
            citations=[Citation(**citation) for citation in citations],
            intents=decision.intents,
            risk_level=decision.risk_level.value,
            evidence_status=evidence.status.value,
            warnings=evidence.warnings,
            confidence=confidence.value,
            requires_professional_advice=decision.risk_level in {RiskLevel.HIGH, RiskLevel.URGENT},
        )


def _build_prompt(
    message: str,
    items: list[EvidenceItem],
    citations: list[dict[str, str | None]],
) -> list[dict[str, str]]:
    citation_lookup = {str(citation["id"]): citation for citation in citations}
    evidence_lines: list[str] = []
    for index, item in enumerate(items, start=1):
        marker = f"S{index}"
        if marker not in citation_lookup:
            continue
        evidence_lines.append(f"[{marker}] {item.title} ({item.source}, {item.trust_tier}): {item.text}")

    system = (
        "You are a pharmacy safety assistant. Answer in Vietnamese, be concise, "
        "use only the supplied evidence, cite claims with source markers like [S1], "
        "and advise professional care for high-risk medication questions. "
        "For symptom triage questions, list possible causes only when supported by evidence, "
        "do not diagnose, explain red flags, and recommend clinical evaluation when appropriate."
    )
    user = f"Question: {message}\n\nEvidence:\n" + (
        "\n".join(evidence_lines) if evidence_lines else "No cited evidence."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _build_hybrid_query(message: str, plan: RetrievalPlan) -> str:
    parts = [message.strip(), " ".join(query for query in plan.queries if query).strip()]
    return " ".join(part for part in parts if part).strip() or message


def _broad_retrieval_plan(plan: RetrievalPlan) -> RetrievalPlan:
    filters = {key: value for key, value in plan.metadata_filters.items() if key != "field"}
    return RetrievalPlan(
        intents=plan.intents,
        risk_level=plan.risk_level,
        queries=plan.queries,
        entities=plan.entities,
        metadata_filters=filters,
    )


def _should_try_web(
    request: ChatRequest,
    evidence: EvidencePackage,
    web_client,
) -> tuple[bool, str]:
    if not request.retrieval_options.allow_web:
        return False, "request_disallows_web"
    if web_client is None:
        return False, "web_client_not_configured"
    if request.retrieval_options.force_web:
        return True, "force_web"
    if evidence.status in {EvidenceStatus.PARTIAL, EvidenceStatus.INSUFFICIENT}:
        return True, f"evidence_status_{evidence.status.value}"
    distinct_sources = {item.url or item.id for item in evidence.items}
    if len(distinct_sources) < 2:
        return True, "narrow_local_sources"
    return False, "local_evidence_sufficient"


def _web_required_entities(request: ChatRequest, required_entities: list[str]) -> list[str]:
    if request.retrieval_options.web_mode == "open":
        return []
    return required_entities


def _has_conflict(items: list[EvidenceItem]) -> bool:
    conflict_terms = ("conflict", "conflicting", "mau thuan", "trai nguoc")
    evidence_text = " ".join(item.text for item in items).lower()
    return any(term in evidence_text for term in conflict_terms)


def _web_sources_to_evidence_items(
    sources: list[WebFetchedSource],
    plan: RetrievalPlan,
) -> list[EvidenceItem]:
    field = _web_evidence_field(plan)
    items: list[EvidenceItem] = []
    for index, source in enumerate(sources, start=1):
        items.append(
            EvidenceItem(
                id=f"web:{source.url or index}",
                text=source.text,
                source=source.source,
                trust_tier=source.trust_tier,
                title=source.title,
                url=source.url,
                score=0.75,
                metadata={"field": field, "source_family": "web_whitelisted"},
            )
        )
    return items


def _web_evidence_field(plan: RetrievalPlan) -> str:
    fields = plan.metadata_filters.get("field", [])
    if fields:
        return fields[0]
    if plan.intents:
        return plan.intents[0]
    return "web"
