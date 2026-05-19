from backend.api.schemas import ChatRequest, ChatResponse, Citation
from core.agent import build_retrieval_plan, route_question
from core.citations import format_citations, has_required_citations
from core.config import get_settings
from core.evidence import assess_evidence, calculate_confidence
from core.llm import ChatModel, EmbeddingModel
from core.models import EvidenceItem, EvidencePackage, EvidenceStatus, RetrievalPlan, RiskLevel
from core.safety import safety_precheck, urgent_response
from core.web_sources import WebFetchedSource


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
        precheck = safety_precheck(request.message)
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
        if "unsupported" in decision.intents:
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

        plan = build_retrieval_plan(decision)
        query_text = " ".join(plan.queries).strip() or request.message
        query_vectors = await self.embedding_model.embed(
            [query_text],
            timeout_seconds=self.settings.embedding_timeout_seconds,
        )
        items = await self.retriever.retrieve(
            plan,
            query_vectors[0],
            timeout_seconds=self.settings.qdrant_query_timeout_seconds,
        )

        required_entities = decision.entities.get("drugs", []) + decision.entities.get("conditions", [])
        evidence = assess_evidence(
            items,
            decision.intents,
            decision.risk_level,
            required_entities,
        )
        web_warnings: list[str] = []
        if (
            request.retrieval_options.allow_web
            and self.web_client is not None
            and evidence.status in {EvidenceStatus.PARTIAL, EvidenceStatus.INSUFFICIENT}
        ):
            try:
                web_sources = await self.web_client.retrieve(
                    plan,
                    query_text=query_text,
                    timeout_seconds=self.settings.web_fetch_timeout_seconds,
                    max_sources=min(
                        request.retrieval_options.max_sources,
                        self.settings.max_web_urls_per_request,
                    ),
                )
            except Exception as exc:
                web_sources = []
                web_warnings.append(f"Web evidence retrieval failed: {exc}")

            if web_sources:
                items = items + _web_sources_to_evidence_items(web_sources, plan)
                evidence = assess_evidence(
                    items,
                    decision.intents,
                    decision.risk_level,
                    required_entities,
                )

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

        if evidence.status == EvidenceStatus.INSUFFICIENT:
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
        "and advise professional care for high-risk medication questions."
    )
    user = f"Question: {message}\n\nEvidence:\n" + (
        "\n".join(evidence_lines) if evidence_lines else "No cited evidence."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


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
