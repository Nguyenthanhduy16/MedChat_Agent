import asyncio
import logging

from backend.api.schemas import ChatRequest, ChatResponse, Citation
from core.agent import route_question
from core.citations import format_citations, has_required_citations
from core.config import get_settings
from core.llm import ChatModel, EmbeddingModel
from core.models import EvidenceItem, EvidenceStatus, RiskLevel, MergedEntities, RouterDecision
from core.query_planner import plan_query_facets, combined_retrieval_plan, retrieval_plan_for_facet
from core.safety import safety_precheck, urgent_response
from core.web_sources import WebFetchedSource

# New pipeline imports
from core.input_normalizer import normalize_input
from core.entity_resolver import resolve_entities
from core.entity_merger import merge_entities
from core.evidence_gate import assess_coverage
from core.answer_synthesizer import build_prompt
from core.post_verifier import verify_answer


logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        chat_model: ChatModel,
        embedding_model: EmbeddingModel,
        retriever,
        web_client=None,
        router_classifier=None,
    ) -> None:
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.retriever = retriever
        self.web_client = web_client
        self.router_classifier = router_classifier
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
        
        # 1. Safety Precheck
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

        # 2. Input Normalization
        normalized = normalize_input(request.message)
        
        # 3. Routing & Classification
        fallback_decision = route_question(request)
        if self.router_classifier is not None and self.settings.llm_router_enabled:
            decision = await self.router_classifier.classify(
                request,
                normalized=normalized,
                fallback_decision=fallback_decision,
                timeout_seconds=self.settings.llm_router_timeout_seconds,
            )
        else:
            decision = fallback_decision
            decision.classification_uncertain = False
            
        logger.info(
            "chat.route intents=%s risk=%s entities=%s needs_context=%s uncertain=%s",
            decision.intents,
            decision.risk_level.value,
            decision.entities,
            decision.needs_context,
            decision.classification_uncertain,
        )
        
        if "unsupported" in decision.intents:
            logger.info("chat.unsupported reason=outside_scope")
            return self._build_unsupported_response(decision)

        # 4. Entity Resolution & Merging
        resolved = await resolve_entities(decision.entities)
        merged_entities = merge_entities(resolved, decision.entities)

        # 5. Query Planning
        query_plan = plan_query_facets(decision)
        plan = combined_retrieval_plan(query_plan, decision)
        
        facet_plans = [retrieval_plan_for_facet(facet, decision) for facet in query_plan.facets]
        facet_query_texts = [_build_hybrid_query(request.message, facet_plan) for facet_plan in facet_plans]
        
        logger.info(
            "chat.retrieval_plan facets=%s",
            [(facet.intent, facet.preferred_fields) for facet in query_plan.facets],
        )
        
        # 6. Retrieval (Vector Search)
        query_vectors = (
            await self.embedding_model.embed(
                facet_query_texts,
                timeout_seconds=self.settings.embedding_timeout_seconds,
            )
            if facet_query_texts
            else []
        )
        
        facet_results: dict[str, list[EvidenceItem]] = {}
        if request.retrieval_options.qdrant_search:
            for facet_plan, query_vector, facet in zip(facet_plans, query_vectors, query_plan.facets, strict=True):
                items = await self.retriever.retrieve(
                    facet_plan,
                    query_vector,
                    timeout_seconds=self.settings.qdrant_query_timeout_seconds,
                )
                for item in items:
                    item.facet_id = facet.intent
                facet_results[facet.intent] = items
        else:
            logger.info("chat.local_retrieval skipped reason=qdrant_search_disabled")

        # Combine items for unified web check
        all_local_items = [item for items in facet_results.values() for item in items]
        logger.info(f"chat.local_retrieval total_count={len(all_local_items)}")

        # 7. Coverage Assessment (Gate)
        coverage = assess_coverage(
            facet_results,
            merged_entities,
            decision.risk_level,
            decision.classification_uncertain,
        )
        logger.info(
            "chat.evidence local_status=%s gaps=%s warnings=%s",
            coverage.status.value,
            coverage.gaps,
            coverage.warnings,
        )

        # 8. Web Fallback
        should_try_web, web_reason = self._should_try_web(request, coverage)
        web_warnings: list[str] = []
        if should_try_web:
            logger.info("chat.web_retrieval start reason=%s", web_reason)
            try:
                # Use the combined plan for web search for simplicity, 
                # or we could do per-facet web search.
                query_text = _build_hybrid_query(request.message, plan)
                web_sources = await self.web_client.retrieve(
                    plan,
                    query_text=query_text,
                    timeout_seconds=self.settings.web_fetch_timeout_seconds,
                    max_sources=min(
                        request.retrieval_options.max_sources,
                        self.settings.max_web_urls_per_request,
                    ),
                    web_mode=request.retrieval_options.web_mode,
                )
                if web_sources:
                    web_items = _web_sources_to_evidence_items(web_sources, plan)
                    # Assign web items to the first missing facet, or a generic 'web' facet
                    if query_plan.facets:
                        facet_id = query_plan.facets[0].intent
                        for item in web_items:
                            item.facet_id = facet_id
                        facet_results.setdefault(facet_id, []).extend(web_items)
                        
                    # Re-assess coverage
                    all_local_items.extend(web_items)
                    coverage = assess_coverage(
                        facet_results,
                        merged_entities,
                        decision.risk_level,
                        decision.classification_uncertain,
                    )
                    logger.info("chat.evidence combined_status=%s", coverage.status.value)
            except Exception as exc:
                web_warnings.append(f"Web evidence retrieval failed: {exc}")
                logger.warning("chat.web_retrieval failed error=%s", exc)

        if web_warnings:
            coverage.warnings.extend(web_warnings)

        # Filter duplicates across facets to prevent over-citation
        unique_items = []
        seen_ids = set()
        for items in facet_results.values():
            for item in items:
                if item.id not in seen_ids:
                    seen_ids.add(item.id)
                    unique_items.append(item)

        citations = format_citations(unique_items, limit=self.settings.final_citations_max)
        logger.info("chat.citations count=%s ids=%s", len(citations), [c["id"] for c in citations])

        # 9. Hard Gate Check
        if coverage.status == EvidenceStatus.INSUFFICIENT:
            logger.info("chat.finish evidence_gate blocked status=insufficient")
            return self._insufficient_evidence_response(request, decision, coverage)

        # 10. Synthesize Answer
        messages = build_prompt(
            request.message,
            query_plan.facets,
            facet_results,
            coverage,
            citations
        )
        logger.info("chat.llm start evidence_count=%s", len(unique_items))
        answer = await self.chat_model.generate(
            messages,
            timeout_seconds=self.settings.llm_timeout_seconds,
        )
        if citations and not has_required_citations(answer, citations):
            answer = f"{answer.rstrip()} [{citations[0]['id']}]"

        # 11. Post Verifier
        verify_result = verify_answer(answer, coverage, decision.risk_level, citations)
        if not verify_result.passed:
            logger.warning("chat.verify_failed reasons=%s", verify_result.failures)
            # Add a safety notice if the LLM hallucinated
            if "Missing high-risk advice" in verify_result.failures[0]:
                answer += "\n\n(Lưu ý: Bạn nên tham khảo ý kiến bác sĩ hoặc dược sĩ trước khi quyết định.)"

        # Confidence mapping for UI
        confidence_val = "high"
        if coverage.status in {EvidenceStatus.WEAK_PARTIAL, EvidenceStatus.CONFLICTING}:
            confidence_val = "low"
        elif coverage.status == EvidenceStatus.USABLE_PARTIAL:
            confidence_val = "medium"

        logger.info(
            "chat.finish status=%s confidence=%s risk=%s",
            coverage.status.value,
            confidence_val,
            decision.risk_level.value,
        )

        return ChatResponse(
            answer=answer,
            safety_notice="Thong tin nay khong thay the tu van truc tiep cua nhan vien y te.",
            citations=[Citation(**citation) for citation in citations],
            intents=decision.intents,
            risk_level=decision.risk_level.value,
            evidence_status=coverage.status.value,
            warnings=coverage.warnings,
            confidence=confidence_val,
            requires_professional_advice=decision.risk_level in {RiskLevel.HIGH, RiskLevel.URGENT},
        )

    def _build_unsupported_response(self, decision: RouterDecision) -> ChatResponse:
        return ChatResponse(
            answer=(
                "Cau hoi nay nam ngoai pham vi duoc/y te cua he thong, "
                "nen toi khong co nguon phu hop de tra loi."
            ),
            safety_notice="He thong chi cung cap thong tin tham khao trong pham vi duoc va y te.",
            citations=[],
            intents=decision.intents,
            risk_level=decision.risk_level.value,
            evidence_status=EvidenceStatus.INSUFFICIENT.value,
            warnings=["Question is outside the configured pharmacy and health scope."],
            confidence="low",
            requires_professional_advice=False,
        )

    def _insufficient_evidence_response(self, request: ChatRequest, decision: RouterDecision, coverage) -> ChatResponse:
        reason_text = " ".join(coverage.gaps)
        
        answer = (
            "Toi chua du bang chung dang tin cay de tra loi an toan cho cau hoi nay. "
            "Bang chung hien co thieu sot nhung phan quan trong so voi yeu cau cua ban.\n"
            "Vui long cung cap them thong tin hoac hoi truc tiep nhan vien y te."
        )
        logger.info("chat.evidence_gate blocked message_len=%s gaps=%s", len(request.message), reason_text)
        return ChatResponse(
            answer=answer,
            safety_notice="Thong tin nay khong thay the tu van truc tiep cua nhan vien y te.",
            citations=[],
            intents=decision.intents,
            risk_level=decision.risk_level.value,
            evidence_status=coverage.status.value,
            warnings=coverage.warnings,
            confidence="low",
            requires_professional_advice=decision.risk_level in {RiskLevel.HIGH, RiskLevel.URGENT},
        )

    def _should_try_web(self, request: ChatRequest, coverage) -> tuple[bool, str]:
        if not request.retrieval_options.allow_web:
            return False, "request_disallows_web"
        if self.web_client is None:
            return False, "web_client_not_configured"
        if request.retrieval_options.force_web:
            return True, "force_web"
        if coverage.status in {EvidenceStatus.WEAK_PARTIAL, EvidenceStatus.INSUFFICIENT, EvidenceStatus.USABLE_PARTIAL}:
            return True, f"evidence_status_{coverage.status.value}"
        return False, "local_evidence_sufficient"


def _build_hybrid_query(message: str, plan) -> str:
    parts = [message.strip(), " ".join(query for query in plan.queries if query).strip()]
    return " ".join(part for part in parts if part).strip() or message


def _web_sources_to_evidence_items(sources: list[WebFetchedSource], plan) -> list[EvidenceItem]:
    field = "web"
    if plan.metadata_filters.get("field"):
        field = plan.metadata_filters["field"][0]
    elif plan.intents:
        field = plan.intents[0]
        
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
