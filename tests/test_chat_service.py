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


def test_get_chat_service_uses_openai_chat_local_e5_and_qdrant(monkeypatch) -> None:
    class FakeLocalEmbeddingModel:
        def __init__(self, model: str) -> None:
            self.model = model

    monkeypatch.setattr(routes, "SentenceTransformerEmbeddingModel", FakeLocalEmbeddingModel)
    monkeypatch.setattr(
        routes,
        "get_settings",
        lambda: routes.Settings(
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
