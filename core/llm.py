import asyncio
import logging
import os
from typing import Protocol

logger = logging.getLogger(__name__)

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


class RerankerModel(Protocol):
    async def score(
        self,
        query: str,
        passages: list[str],
        timeout_seconds: float,
    ) -> list[float]:
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


class FlagEmbeddingRerankerModel:
    def __init__(self, model: str, use_fp16: bool = True) -> None:
        import torch
        from FlagEmbedding import FlagReranker

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("reranker.init model=%s device=%s fp16=%s", model, device, use_fp16)
        self.model = model
        try:
            self.reranker = FlagReranker(model, use_fp16=use_fp16, device=device)
        except TypeError:
            self.reranker = FlagReranker(model, use_fp16=use_fp16)
        ensure_prepare_for_model_compat(getattr(self.reranker, "tokenizer", None))

    async def score(
        self,
        query: str,
        passages: list[str],
        timeout_seconds: float,
    ) -> list[float]:
        pairs = [[query, passage] for passage in passages]
        scores = await asyncio.wait_for(
            asyncio.to_thread(self.reranker.compute_score, pairs, normalize=True),
            timeout=timeout_seconds,
        )
        return [float(score) for score in scores]


class FallbackChatModel:
    def __init__(self, primary: ChatModel, secondary: ChatModel) -> None:
        self.primary = primary
        self.secondary = secondary

    async def generate(self, messages: list[dict[str, str]], timeout_seconds: float) -> str:
        try:
            return await self.primary.generate(messages, timeout_seconds)
        except Exception:
            return await self.secondary.generate(messages, timeout_seconds)


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


class GeminiChatModel:
    def __init__(
        self,
        api_key: str,
        model: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.http_client = http_client or httpx.AsyncClient(base_url="https://generativelanguage.googleapis.com")

    async def generate(self, messages: list[dict[str, str]], timeout_seconds: float) -> str:
        response = await self.http_client.post(
            f"/v1beta/models/{self.model}:generateContent",
            params={"key": self.api_key},
            json=_gemini_payload(messages),
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        parts = payload["candidates"][0]["content"].get("parts", [])
        return "".join(str(part.get("text", "")) for part in parts)


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
        import torch
        from sentence_transformers import SentenceTransformer

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("embedding.init model=%s device=%s", model, device)
        try:
            self.model = SentenceTransformer(model, device=device)
        except TypeError:
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


def ensure_prepare_for_model_compat(tokenizer) -> None:
    if tokenizer is None or hasattr(tokenizer, "prepare_for_model"):
        return

    def prepare_for_model(
        ids,
        pair_ids=None,
        truncation=False,
        max_length=None,
        padding=False,
        **kwargs,
    ):
        first = list(ids)
        second = list(pair_ids or [])
        pair_mode = pair_ids is not None
        special_count = 4 if pair_mode else 2
        if max_length is not None:
            available = max(max_length - special_count, 0)
            if truncation == "only_second" and pair_mode:
                second = second[: max(available - len(first), 0)]
            elif pair_mode:
                first = first[:available]
                second = second[: max(available - len(first), 0)]
            else:
                first = first[:available]

        cls_token_id = getattr(tokenizer, "cls_token_id", None)
        sep_token_id = getattr(tokenizer, "sep_token_id", None)
        if cls_token_id is None or sep_token_id is None:
            raise AttributeError("Tokenizer lacks prepare_for_model and special token ids for compatibility shim.")

        if pair_mode:
            input_ids = [cls_token_id] + first + [sep_token_id, sep_token_id] + second + [sep_token_id]
        else:
            input_ids = [cls_token_id] + first + [sep_token_id]

        attention_mask = [1] * len(input_ids)
        if padding == "max_length" and max_length is not None:
            pad_token_id = getattr(tokenizer, "pad_token_id", 0)
            pad_len = max(max_length - len(input_ids), 0)
            input_ids = input_ids + [pad_token_id] * pad_len
            attention_mask = attention_mask + [0] * pad_len
        return {"input_ids": input_ids, "attention_mask": attention_mask}

    tokenizer.prepare_for_model = prepare_for_model


def _gemini_payload(messages: list[dict[str, str]]) -> dict:
    contents: list[dict] = []
    system_parts: list[dict[str, str]] = []
    for message in messages:
        role = message.get("role", "user")
        text = message.get("content", "")
        if role == "system":
            system_parts.append({"text": text})
            continue
        contents.append(
            {
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": text}],
            }
        )

    payload: dict = {"contents": contents}
    if system_parts:
        payload["systemInstruction"] = {"parts": system_parts}
    return payload
