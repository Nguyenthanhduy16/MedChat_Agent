from pathlib import Path

from fastapi import APIRouter, HTTPException
from qdrant_client import AsyncQdrantClient

from backend.api.schemas import ChatRequest, ChatResponse, IngestResponse, SourceStatusResponse
from core.chat_service import ChatService
from core.config import Settings, get_settings
from core.ingestion import ingest_directory_async
from core.llm import OpenAIChatModel, SentenceTransformerEmbeddingModel
from core.retrieval import QdrantRetriever


router = APIRouter()


def get_chat_service() -> ChatService:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to use /chat with real providers.")

    qdrant_client = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        check_compatibility=False,
    )
    return ChatService(
        chat_model=OpenAIChatModel(api_key=settings.openai_api_key, model=settings.chat_model),
        embedding_model=SentenceTransformerEmbeddingModel(model=settings.embedding_model),
        retriever=QdrantRetriever(qdrant_client, settings.qdrant_collection),
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        return await get_chat_service().chat(request)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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
def source_status() -> SourceStatusResponse:
    settings = get_settings()
    return SourceStatusResponse(collection=settings.qdrant_collection, source_families=[], qdrant_ready=False)
