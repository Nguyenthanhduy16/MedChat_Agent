import sys
import types

import pytest
from fastapi.testclient import TestClient

import backend.api.routes as routes
from backend.api.schemas import ChatRequest
from backend.main import create_app
from core.chat_service import ChatService
from core.config import Settings
from core.llm import FakeChatModel, FakeEmbeddingModel, OpenAIChatModel, OpenAIEmbeddingModel
from core.models import EvidenceItem
from core.retrieval import QdrantRetriever
from core.web_sources import DomainNotAllowedError, WebFetchedSource


@pytest.mark.asyncio
async def test_fake_llm_and_embedding_models() -> None:
    chat = FakeChatModel(answer="Answer with [S1].")
    embedding = FakeEmbeddingModel(size=4)

    answer = await chat.generate([{"role": "user", "content": "hello"}], timeout_seconds=1)
    vectors = await embedding.embed(["abc", "def"], timeout_seconds=1)

    assert answer == "Answer with [S1]."
    assert vectors == [[3.0, 0.0, 0.0, 0.0], [3.0, 0.0, 0.0, 0.0]]


@pytest.mark.asyncio
async def test_sentence_transformer_embedding_model_uses_e5_prefixes(monkeypatch) -> None:
    class FakeSentenceTransformer:
        calls: list[list[str]] = []

        def __init__(self, model_name: str) -> None:
            self.model_name = model_name

        def encode(self, texts: list[str], normalize_embeddings: bool) -> list[list[float]]:
            self.calls.append(texts)
            assert normalize_embeddings is True
            return [[float(len(text)), 0.0] for text in texts]

    fake_module = types.SimpleNamespace(SentenceTransformer=FakeSentenceTransformer)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    from core.llm import SentenceTransformerEmbeddingModel

    model = SentenceTransformerEmbeddingModel("intfloat/multilingual-e5-base")

    query_vectors = await model.embed(["warfarin"], timeout_seconds=1)
    passage_vectors = await model.embed(["Hoạt chất: Abacavir"], timeout_seconds=1, input_type="passage")

    assert FakeSentenceTransformer.calls == [["query: warfarin"], ["passage: Hoạt chất: Abacavir"]]
    assert query_vectors == [[float(len("query: warfarin")), 0.0]]
    assert passage_vectors == [[float(len("passage: Hoạt chất: Abacavir")), 0.0]]


class FakeRetriever:
    async def retrieve(self, plan, query_vector, timeout_seconds):
        return [
            EvidenceItem(
                id="1",
                text="Warfarin and ibuprofen may increase bleeding risk.",
                source="DailyMed",
                trust_tier="regulatory",
                title="Warfarin label",
                url="https://dailymed.nlm.nih.gov/warfarin",
                score=0.95,
                metadata={"field": "interaction"},
            ),
            EvidenceItem(
                id="2",
                text="NSAIDs including ibuprofen may increase bleeding risk.",
                source="FDA",
                trust_tier="regulatory",
                title="Ibuprofen label",
                url="https://fda.gov/ibuprofen",
                score=0.90,
                metadata={"field": "contraindication"},
            ),
        ]


class EmptyRetriever:
    async def retrieve(self, plan, query_vector, timeout_seconds):
        return []


class TrackingRetriever:
    def __init__(self) -> None:
        self.calls = 0

    async def retrieve(self, plan, query_vector, timeout_seconds):
        self.calls += 1
        return [
            EvidenceItem(
                id="unrelated",
                text="Kho tho hut hoi la mot trieu chung ho hap.",
                source="Pharmacity",
                trust_tier="local_curated",
                title="Kho tho",
                url="https://www.pharmacity.vn/benh/kho-tho-hut-hoi.html",
                score=0.92,
                metadata={"field": "prevention"},
            )
        ]


class FakeWebClient:
    def __init__(self) -> None:
        self.calls = 0

    async def retrieve(self, plan, query_text: str, timeout_seconds: float, max_sources: int):
        self.calls += 1
        assert query_text
        assert max_sources == 5
        return [
            WebFetchedSource(
                title="Abacavir label",
                url="https://dailymed.nlm.nih.gov/abacavir",
                source="dailymed.nlm.nih.gov",
                text="Abacavir is indicated for treatment of HIV infection in adults and children.",
                trust_tier="regulatory",
            )
        ]


@pytest.mark.asyncio
async def test_chat_service_returns_structured_grounded_answer() -> None:
    service = ChatService(
        chat_model=FakeChatModel("Ibuprofen va warfarin co the lam tang nguy co chay mau [S1]."),
        embedding_model=FakeEmbeddingModel(size=4),
        retriever=FakeRetriever(),
    )

    response = await service.chat(ChatRequest(message="Toi dang uong warfarin, co dung ibuprofen duoc khong?"))

    assert response.risk_level == "high"
    assert response.evidence_status == "sufficient"
    assert response.citations[0].id == "S1"
    assert response.requires_professional_advice is True


@pytest.mark.asyncio
async def test_chat_service_uses_whitelisted_web_when_local_evidence_is_insufficient() -> None:
    web_client = FakeWebClient()
    service = ChatService(
        chat_model=FakeChatModel("Abacavir duoc dung de dieu tri HIV [S1]."),
        embedding_model=FakeEmbeddingModel(size=4),
        retriever=EmptyRetriever(),
        web_client=web_client,
    )

    response = await service.chat(
        ChatRequest(
            message="Abacavir dung de lam gi?",
            retrieval_options={"allow_web": True, "max_sources": 8},
        )
    )

    assert web_client.calls == 1
    assert response.evidence_status == "sufficient"
    assert response.citations[0].url == "https://dailymed.nlm.nih.gov/abacavir"
    assert response.citations[0].trust_tier == "regulatory"
    assert response.answer.endswith("[S1].") or "[S1]" in response.answer


@pytest.mark.asyncio
async def test_chat_service_does_not_use_web_when_request_disallows_web() -> None:
    web_client = FakeWebClient()
    service = ChatService(
        chat_model=FakeChatModel("unused"),
        embedding_model=FakeEmbeddingModel(size=4),
        retriever=EmptyRetriever(),
        web_client=web_client,
    )

    response = await service.chat(
        ChatRequest(
            message="Abacavir dung de lam gi?",
            retrieval_options={"allow_web": False, "max_sources": 8},
        )
    )

    assert web_client.calls == 0
    assert response.evidence_status == "insufficient"
    assert response.citations == []


@pytest.mark.asyncio
async def test_chat_service_fails_closed_for_non_medical_question_without_retrieval() -> None:
    retriever = TrackingRetriever()
    web_client = FakeWebClient()
    service = ChatService(
        chat_model=FakeChatModel("This should not be used [S1]."),
        embedding_model=FakeEmbeddingModel(size=4),
        retriever=retriever,
        web_client=web_client,
    )

    response = await service.chat(
        ChatRequest(
            message="Cach dat A+ Giai tich",
            retrieval_options={"allow_web": True, "max_sources": 8},
        )
    )

    assert retriever.calls == 0
    assert web_client.calls == 0
    assert response.intents == ["unsupported"]
    assert response.evidence_status == "insufficient"
    assert response.confidence == "low"
    assert response.citations == []
    assert "ngoai pham vi" in response.answer.lower()


@pytest.mark.asyncio
async def test_chat_service_does_not_cite_unrelated_local_evidence_for_named_drug() -> None:
    service = ChatService(
        chat_model=FakeChatModel("This should not be used [S1]."),
        embedding_model=FakeEmbeddingModel(size=4),
        retriever=TrackingRetriever(),
    )

    response = await service.chat(
        ChatRequest(
            message="Thuoc Zoacnel 5mg Davi",
            retrieval_options={"allow_web": False, "max_sources": 8},
        )
    )

    assert response.intents == ["drug_identity"]
    assert response.evidence_status == "insufficient"
    assert response.confidence == "low"
    assert response.citations == []
    assert "Zoacnel" not in response.answer or "chua co du bang chung" in response.answer


@pytest.mark.asyncio
async def test_chat_service_fails_closed_when_web_retrieval_fails() -> None:
    class FailingWebClient:
        async def retrieve(self, plan, query_text: str, timeout_seconds: float, max_sources: int):
            raise DomainNotAllowedError("URL host is not allowed: https://example.com/drug")

    service = ChatService(
        chat_model=FakeChatModel("unused"),
        embedding_model=FakeEmbeddingModel(size=4),
        retriever=EmptyRetriever(),
        web_client=FailingWebClient(),
    )

    response = await service.chat(
        ChatRequest(
            message="Abacavir dung de lam gi?",
            retrieval_options={"allow_web": True, "max_sources": 8},
        )
    )

    assert response.evidence_status == "insufficient"
    assert response.citations == []
    assert any("Web evidence retrieval failed" in warning for warning in response.warnings)


@pytest.mark.asyncio
async def test_chat_service_short_circuits_urgent_request() -> None:
    service = ChatService(
        chat_model=FakeChatModel("unused"),
        embedding_model=FakeEmbeddingModel(size=4),
        retriever=FakeRetriever(),
    )

    response = await service.chat(ChatRequest(message="Toi uong qua lieu thuoc X va dang kho tho"))

    assert response.risk_level == "urgent"
    assert response.confidence == "medium"
    assert response.requires_professional_advice is True


def test_health_route() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_route_reports_missing_openai_key(monkeypatch) -> None:
    monkeypatch.setattr(routes.get_settings, "cache_clear", lambda: None, raising=False)
    monkeypatch.setattr(routes, "get_settings", lambda: routes.Settings(openai_api_key=None))
    client = TestClient(create_app())

    response = client.post("/chat", json={"message": "Warfarin va ibuprofen co tuong tac khong?"})

    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_embedding_defaults_use_multilingual_e5_base() -> None:
    settings = Settings(_env_file=None)

    assert settings.embedding_model == "intfloat/multilingual-e5-base"
    assert settings.qdrant_vector_size == 768
    assert settings.web_search_endpoint is None
    assert settings.web_search_api_key is None
    assert settings.web_search_provider == "generic"


def test_get_chat_service_uses_openai_chat_local_e5_and_qdrant(monkeypatch) -> None:
    routes.get_chat_service.cache_clear()

    class FakeLocalEmbeddingModel:
        def __init__(self, model: str) -> None:
            self.model = model

    monkeypatch.setattr(routes, "SentenceTransformerEmbeddingModel", FakeLocalEmbeddingModel)
    monkeypatch.setattr(
        routes,
        "get_settings",
        lambda: routes.Settings(
            _env_file=None,
            openai_api_key="test-key",
            chat_model="chat-test",
            embedding_model="embed-test",
            qdrant_url="https://qdrant.test:6333",
            qdrant_api_key="qdrant-key",
            qdrant_collection="test_collection",
        ),
    )

    service = routes.get_chat_service()

    assert isinstance(service.chat_model, OpenAIChatModel)
    assert isinstance(service.embedding_model, FakeLocalEmbeddingModel)
    assert service.embedding_model.model == "embed-test"
    assert isinstance(service.retriever, QdrantRetriever)
    assert isinstance(service.web_client, routes.WebSourceClient)
    assert service.web_client.search_provider is None


def test_get_chat_service_configures_http_search_provider_when_endpoint_exists(monkeypatch) -> None:
    routes.get_chat_service.cache_clear()

    class FakeLocalEmbeddingModel:
        def __init__(self, model: str) -> None:
            self.model = model

    monkeypatch.setattr(routes, "SentenceTransformerEmbeddingModel", FakeLocalEmbeddingModel)
    monkeypatch.setattr(
        routes,
        "get_settings",
        lambda: routes.Settings(
            _env_file=None,
            openai_api_key="test-key",
            web_search_endpoint="https://search.test/api",
            web_search_api_key="search-key",
        ),
    )

    service = routes.get_chat_service()

    assert isinstance(service.web_client.search_provider, routes.HTTPJSONSearchProvider)
    assert service.web_client.search_provider.endpoint == "https://search.test/api"
    assert service.web_client.search_provider.api_key == "search-key"


def test_get_chat_service_configures_tavily_search_provider(monkeypatch) -> None:
    routes.get_chat_service.cache_clear()

    class FakeLocalEmbeddingModel:
        def __init__(self, model: str) -> None:
            self.model = model

    monkeypatch.setattr(routes, "SentenceTransformerEmbeddingModel", FakeLocalEmbeddingModel)
    monkeypatch.setattr(
        routes,
        "get_settings",
        lambda: routes.Settings(
            _env_file=None,
            openai_api_key="test-key",
            web_search_provider="tavily",
            web_search_endpoint="https://api.tavily.com/search",
            web_search_api_key="tvly-test",
        ),
    )

    service = routes.get_chat_service()

    assert isinstance(service.web_client.search_provider, routes.TavilySearchProvider)
    assert service.web_client.search_provider.endpoint == "https://api.tavily.com/search"
    assert service.web_client.search_provider.api_key == "tvly-test"


def test_source_status_reports_qdrant_collection_and_source_families(monkeypatch) -> None:
    class FakePoint:
        def __init__(self, source_family: str) -> None:
            self.payload = {"source_family": source_family}

    class FakeQdrantClient:
        def __init__(self, url: str, api_key: str | None, check_compatibility: bool) -> None:
            self.url = url
            self.api_key = api_key
            self.check_compatibility = check_compatibility

        async def collection_exists(self, collection_name: str) -> bool:
            assert collection_name == "test_collection"
            return True

        async def scroll(self, collection_name: str, limit: int, with_payload: list[str], with_vectors: bool):
            assert collection_name == "test_collection"
            assert limit == 100
            assert with_payload == ["source_family"]
            assert with_vectors is False
            return [FakePoint("longchau_ingredients_chunked"), FakePoint("pharmacity_chunked")], None

    monkeypatch.setattr(routes, "AsyncQdrantClient", FakeQdrantClient)
    monkeypatch.setattr(
        routes,
        "get_settings",
        lambda: routes.Settings(
            qdrant_url="https://qdrant.test:6333",
            qdrant_api_key="qdrant-key",
            qdrant_collection="test_collection",
        ),
    )
    client = TestClient(create_app())

    response = client.get("/sources/status")

    assert response.status_code == 200
    assert response.json() == {
        "collection": "test_collection",
        "source_families": ["longchau_ingredients_chunked", "pharmacity_chunked"],
        "qdrant_ready": True,
    }


def test_source_status_fails_soft_when_qdrant_is_unavailable(monkeypatch) -> None:
    class FakeQdrantClient:
        def __init__(self, url: str, api_key: str | None, check_compatibility: bool) -> None:
            pass

        async def collection_exists(self, collection_name: str) -> bool:
            raise RuntimeError("connection refused")

    monkeypatch.setattr(routes, "AsyncQdrantClient", FakeQdrantClient)
    monkeypatch.setattr(routes, "get_settings", lambda: routes.Settings(qdrant_collection="test_collection"))
    client = TestClient(create_app())

    response = client.get("/sources/status")

    assert response.status_code == 200
    assert response.json() == {
        "collection": "test_collection",
        "source_families": [],
        "qdrant_ready": False,
    }
