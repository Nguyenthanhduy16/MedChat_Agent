from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MedChat Pharmacy Agent"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    chat_model: str = "gpt-4.1-mini"
    router_model: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    llm_router_enabled: bool = True
    llm_router_confidence_threshold: float = 0.6
    llm_router_timeout_seconds: float = 8.0
    embedding_model: str = "intfloat/multilingual-e5-base"
    reranker_model: str | None = None
    reranker_top_k: int = 10
    reranker_timeout_seconds: float = 10.0
    reranker_use_fp16: bool = True
    reranker_device: str = "auto"
    reranker_batch_size: int = 16
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "pharmacy_chunks"
    qdrant_vector_size: int = 768
    api_request_body_kb: int = 64
    chat_timeout_seconds: float = 60.0
    llm_timeout_seconds: float = 30.0
    embedding_timeout_seconds: float = 60.0
    qdrant_query_timeout_seconds: float = 5.0
    qdrant_upsert_timeout_seconds: float = 120.0
    web_search_provider: str = "generic"
    web_search_endpoint: str | None = None
    web_search_api_key: str | None = None
    web_search_timeout_seconds: float = 8.0
    web_fetch_timeout_seconds: float = 5.0
    max_web_urls_per_request: int = 10
    max_evidence_chunks_for_llm: int = 12
    local_top_k_per_intent: int = 6
    final_citations_min: int = 3
    final_citations_max: int = 8
    ingestion_batch_size: int = 64
    whitelist_domains: list[str] = Field(
        default_factory=lambda: [
            "vinmec.com",
            "suckhoedoisong.vn",
            "thuocbietduoc.com.vn",
            "duocdienvietnam.com",
            "tudu.com.vn",
            "nhathuoclongchau.com.vn",
            "pharmacity.vn",
            "nhathuocankhang.com",
        ]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
