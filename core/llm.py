import asyncio
import os
from typing import Protocol

import httpx
from openai import AsyncOpenAI

# Buộc sentence-transformers/huggingface dùng model đã cache cục bộ,
# không kết nối lên huggingface.co để verify/tải lại model.
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")


class ChatModel(Protocol):
    async def generate(self, messages: list[dict[str, str]], timeout_seconds: float) -> str:
        raise NotImplementedError


class EmbeddingModel(Protocol):
    async def embed(
        self,
        texts: list[str],
        timeout_seconds: float,
        input_type: str = "query",
    ) -> list[list[float]]:
        raise NotImplementedError


class FakeChatModel:
    def __init__(self, answer: str) -> None:
        self.answer = answer

    async def generate(self, messages: list[dict[str, str]], timeout_seconds: float) -> str:
        return self.answer


class FakeEmbeddingModel:
    def __init__(self, size: int = 1536) -> None:
        self.size = size

    async def embed(
        self,
        texts: list[str],
        timeout_seconds: float,
        input_type: str = "query",
    ) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.size
            vector[0] = float(len(text))
            vectors.append(vector)
        return vectors


class OpenAIChatModel:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key, http_client=httpx.AsyncClient())
        self.model = model

    async def generate(self, messages: list[dict[str, str]], timeout_seconds: float) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            timeout=timeout_seconds,
        )
        content = response.choices[0].message.content
        return content or ""


class OpenAIEmbeddingModel:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key, http_client=httpx.AsyncClient())
        self.model = model

    async def embed(
        self,
        texts: list[str],
        timeout_seconds: float,
        input_type: str = "query",
    ) -> list[list[float]]:
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
            timeout=timeout_seconds,
        )
        return [item.embedding for item in response.data]


class SentenceTransformerEmbeddingModel:
    def __init__(self, model: str) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model)

    async def embed(
        self,
        texts: list[str],
        timeout_seconds: float,
        input_type: str = "query",
    ) -> list[list[float]]:
        prefix = _e5_prefix(input_type)
        prefixed = [f"{prefix}: {text}" for text in texts]
        embeddings = await asyncio.wait_for(
            asyncio.to_thread(self.model.encode, prefixed, normalize_embeddings=True),
            timeout=timeout_seconds,
        )
        return [list(map(float, vector)) for vector in embeddings]


def _e5_prefix(input_type: str) -> str:
    if input_type == "passage":
        return "passage"
    return "query"
