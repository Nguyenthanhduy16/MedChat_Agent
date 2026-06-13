from functools import lru_cache
from pathlib import Path
import logging
import traceback

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from qdrant_client import AsyncQdrantClient

from backend.api.schemas import ChatRequest, ChatResponse, IngestResponse, SourceStatusResponse
from core.chat_service import ChatService
from core.config import Settings, get_settings
from core.ingestion import ingest_directory_async
from core.llm import (
    FallbackChatModel,
    FlagEmbeddingRerankerModel,
    GeminiChatModel,
    OpenAIChatModel,
    SentenceTransformerEmbeddingModel,
)
from core.retrieval import QdrantRetriever
from core.router_classifier import LLMRouterClassifier
from core.web_sources import HTTPJSONSearchProvider, TavilySearchProvider, WebSourceClient

logger = logging.getLogger(__name__)

router = APIRouter()


@lru_cache
def get_chat_service() -> ChatService:
    """Singleton: chỉ khởi tạo ChatService (bao gồm load model embedding) một lần duy nhất."""
    settings = get_settings()
    chat_model = _build_chat_model(settings)
    router_model = _build_chat_model(settings, model_override=settings.router_model) if settings.router_model else chat_model
    
    router_classifier = (
        LLMRouterClassifier(
            router_model,
            confidence_threshold=settings.llm_router_confidence_threshold,
        )
        if settings.llm_router_enabled
        else None
    )

    qdrant_client = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        check_compatibility=False,
        timeout=60.0,
    )
    reranker = (
        FlagEmbeddingRerankerModel(
            model=settings.reranker_model,
            use_fp16=settings.reranker_use_fp16,
        )
        if settings.reranker_model
        else None
    )
    search_provider = _build_search_provider(settings)
    return ChatService(
        chat_model=chat_model,
        embedding_model=SentenceTransformerEmbeddingModel(model=settings.embedding_model),
        retriever=QdrantRetriever(
            qdrant_client,
            settings.qdrant_collection,
            reranker=reranker,
            reranker_top_k=settings.reranker_top_k,
            reranker_timeout_seconds=settings.reranker_timeout_seconds,
        ),
        web_client=WebSourceClient(settings.whitelist_domains, search_provider=search_provider),
        router_classifier=router_classifier,
    )


def _build_chat_model(settings: Settings, model_override: str | None = None):
    target_model = model_override or settings.chat_model
    openai_model = (
        OpenAIChatModel(
            api_key=settings.openai_api_key, 
            model=target_model,
            base_url=settings.openai_base_url,
        )
        if settings.openai_api_key
        else None
    )
    gemini_model = (
        GeminiChatModel(api_key=settings.gemini_api_key, model=settings.gemini_model)
        if settings.gemini_api_key
        else None
    )
    if openai_model and gemini_model:
        return FallbackChatModel(primary=openai_model, secondary=gemini_model)
    if openai_model:
        return openai_model
    if gemini_model:
        return gemini_model
    raise RuntimeError("OPENAI_API_KEY or GEMINI_API_KEY is required to use /chat with real providers.")


def _build_search_provider(settings: Settings):
    if not settings.web_search_endpoint:
        return None
    provider = settings.web_search_provider.lower().strip()
    if provider == "tavily":
        if not settings.web_search_api_key:
            raise RuntimeError("WEB_SEARCH_API_KEY is required when WEB_SEARCH_PROVIDER=tavily.")
        return TavilySearchProvider(settings.web_search_endpoint, settings.web_search_api_key)
    return HTTPJSONSearchProvider(settings.web_search_endpoint, settings.web_search_api_key)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        return await get_chat_service().chat(request)
    except Exception as exc:
        logger.error("Chat endpoint error:\n%s", traceback.format_exc())
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    async def event_generator():
        import json
        yield (
            "data: "
            + json.dumps(
                {
                    "type": "trace",
                    "step": "connect",
                    "message": "Đang kết nối tới máy chủ...",
                },
                ensure_ascii=False,
            )
            + "\n\n"
        ).encode("utf-8")
        try:
            async for event in get_chat_service().chat_stream(request):
                yield event.encode("utf-8")
        except Exception as exc:
            logger.error("Chat stream endpoint error:\n%s", traceback.format_exc())
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n".encode("utf-8")

    return StreamingResponse(event_generator(), media_type="text/event-stream; charset=utf-8")


@router.post("/ingest", response_model=IngestResponse)
async def ingest() -> IngestResponse:
    settings = get_settings()
    qdrant_client = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        check_compatibility=False,
    )
    report = await ingest_directory_async(
        Path("data/chunks"),
        embedding_model=SentenceTransformerEmbeddingModel(model=settings.embedding_model),
        qdrant_client=qdrant_client,
        settings=settings,
    )
    return IngestResponse(
        indexed=int(report["indexed"]),
        skipped=int(report["skipped"]),
        errors=list(report["errors"]),
    )


@router.get("/sources/status", response_model=SourceStatusResponse)
async def source_status() -> SourceStatusResponse:
    settings = get_settings()
    qdrant_client = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        check_compatibility=False,
    )
    try:
        collection_exists = await qdrant_client.collection_exists(collection_name=settings.qdrant_collection)
        if not collection_exists:
            return SourceStatusResponse(
                collection=settings.qdrant_collection,
                source_families=[],
                qdrant_ready=False,
            )

        points, _ = await qdrant_client.scroll(
            collection_name=settings.qdrant_collection,
            limit=100,
            with_payload=["source_family"],
            with_vectors=False,
        )
    except Exception:
        return SourceStatusResponse(collection=settings.qdrant_collection, source_families=[], qdrant_ready=False)

    source_families = sorted(
        {
            str(point.payload["source_family"])
            for point in points
            if point.payload and point.payload.get("source_family")
        }
    )
    return SourceStatusResponse(
        collection=settings.qdrant_collection,
        source_families=source_families,
        qdrant_ready=True,
    )
