import asyncio
import logging
import os
import time
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

    async def stream(self, messages: list[dict[str, str]], timeout_seconds: float):
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

    async def stream(self, messages: list[dict[str, str]], timeout_seconds: float):
        words = self.answer.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")


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
    def __init__(
        self,
        model: str,
        use_fp16: bool = True,
        device: str = "auto",
        batch_size: int = 16,
    ) -> None:
        import torch
        from FlagEmbedding import FlagReranker

        resolved_device = device
        if resolved_device == "auto":
            resolved_device = "cuda" if torch.cuda.is_available() else "cpu"
        effective_fp16 = bool(use_fp16 and resolved_device != "cpu")
        # On Windows, passing devices=['cpu'] explicitly to FlagReranker triggers a
        # native access violation in the underlying C++ runtime. When no GPU is present
        # and the effective device is 'cpu', let FlagReranker auto-detect rather than
        # forcing devices=['cpu']. We still track resolved_device for logging/warmup.
        build_device = "auto" if resolved_device == "cpu" else resolved_device
        start = time.perf_counter()
        logger.info(
            "reranker.init model=%s device=%s fp16=%s batch_size=%s",
            model,
            resolved_device,
            effective_fp16,
            batch_size,
        )
        self.model = model
        self._score_lock = asyncio.Lock()
        self.reranker = self._build_reranker(
            FlagReranker,
            model=model,
            use_fp16=effective_fp16,
            device=build_device,
            batch_size=batch_size,
        )
        self._patch_reranker_tqdm(self.reranker)
        self._compute_score_kwargs = {}
        ensure_prepare_for_model_compat(getattr(self.reranker, "tokenizer", None))
        # Warmup: force model.to(device) on the main thread so that CUDA context
        # is initialized before asyncio.to_thread calls. On Windows WDDM, CUDA
        # context must be initialized on the thread that first uses it; a dummy
        # score call achieves this and pre-JITs the CUDA kernels.
        if resolved_device != "cpu" and hasattr(self.reranker, "model"):
            self._warmup_on_device(resolved_device)
        actual_device = self._actual_model_device()
        logger.info(
            "reranker.ready model=%s target_device=%s actual_device=%s fp16=%s elapsed_seconds=%.2f",
            model,
            resolved_device,
            actual_device,
            effective_fp16,
            time.perf_counter() - start,
        )

    @staticmethod
    def _build_reranker(FlagReranker, model: str, use_fp16: bool, device: str, batch_size: int):
        # FlagReranker uses `devices` (plural) parameter to specify the target device.
        # We pass device as a list so AbsReranker.get_target_devices() picks it up correctly.
        devices_arg = [device] if device not in ("auto", None) else None
        base_kwargs = {
            "use_fp16": use_fp16,
            "batch_size": batch_size,
        }
        attempts = (
            {**base_kwargs, "devices": devices_arg},
            {**base_kwargs, "device": device},
            base_kwargs,
        )
        last_error: TypeError | None = None
        for kwargs in attempts:
            try:
                return FlagReranker(model, **kwargs)
            except TypeError as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError("Unable to initialize FlagEmbedding reranker")

    def _actual_model_device(self) -> str:
        model = getattr(self.reranker, "model", None)
        if model is None or not hasattr(model, "parameters"):
            return "unknown"
        try:
            return str(next(model.parameters()).device)
        except (AttributeError, StopIteration, TypeError):
            return "unknown"

    def _warmup_on_device(self, device: str) -> None:
        """Force model.to(device) on the calling (main) thread.

        FlagEmbedding's compute_score_single_gpu lazily calls model.to(device)
        at inference time. On Windows WDDM, calling model.to('cuda') from
        asyncio.to_thread worker threads can silently fall back to CPU because
        the CUDA context hasn't been initialized on that thread yet.
        Running one dummy score here pins the model to GPU on the main thread
        so subsequent calls from worker threads find it already on the device.
        """
        try:
            self.reranker.compute_score(
                [["warmup query", "warmup passage"]],
                normalize=False,
                **self._compute_score_kwargs,
            )
            actual = self._actual_model_device()
            logger.info("reranker warmup complete: model pinned to device=%s", actual)
        except (AssertionError, AttributeError, RuntimeError, TypeError) as exc:
            logger.warning(
                "reranker warmup failed for device=%s (%s); model will run on CPU. "
                "Install a CUDA-enabled PyTorch: pip install torch --index-url https://download.pytorch.org/whl/cu124",
                device, exc,
            )

    @staticmethod
    def _patch_reranker_tqdm(reranker: object) -> None:
        """Monkey-patch compute_score_single_gpu so FlagEmbedding's internal
        tqdm/trange calls are silenced.  We replace the tqdm & trange names
        inside the method's enclosing module with no-op stubs."""
        try:
            import FlagEmbedding.inference.reranker.encoder_only.base as _flag_base
            from tqdm import tqdm as _real_tqdm

            class _SilentTqdm(_real_tqdm):
                def __init__(self, *args, **kwargs):
                    kwargs["disable"] = True
                    super().__init__(*args, **kwargs)

            _flag_base.tqdm = _SilentTqdm
            _flag_base.trange = lambda *a, **kw: _SilentTqdm(range(*a[:3]) if a else [], **kw)
        except Exception:
            pass

    async def score(
        self,
        query: str,
        passages: list[str],
        timeout_seconds: float,
    ) -> list[float]:
        pairs = [[query, passage] for passage in passages]
        async with self._score_lock:
            scores = await asyncio.wait_for(
                asyncio.to_thread(
                    self.reranker.compute_score,
                    pairs,
                    normalize=True,
                    **self._compute_score_kwargs,
                ),
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

    async def stream(self, messages: list[dict[str, str]], timeout_seconds: float):
        try:
            generator = self.primary.stream(messages, timeout_seconds)
            try:
                first_chunk = await generator.__anext__()
            except StopAsyncIteration:
                return
            yield first_chunk
            async for chunk in generator:
                yield chunk
        except Exception:
            async for chunk in self.secondary.stream(messages, timeout_seconds):
                yield chunk


class OpenAIChatModel:
    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        kwargs = {"api_key": api_key, "http_client": httpx.AsyncClient()}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = AsyncOpenAI(**kwargs)
        self.model = model

    async def generate(self, messages: list[dict[str, str]], timeout_seconds: float) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            timeout=timeout_seconds,
            max_tokens=1500,
        )
        content = response.choices[0].message.content
        return content or ""

    async def stream(self, messages: list[dict[str, str]], timeout_seconds: float):
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            timeout=timeout_seconds,
            max_tokens=1500,
            stream=True,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


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

    async def stream(self, messages: list[dict[str, str]], timeout_seconds: float):
        import json
        async with self.http_client.stream(
            "POST",
            f"/v1beta/models/{self.model}:streamGenerateContent?alt=sse",
            params={"key": self.api_key},
            json=_gemini_payload(messages),
            timeout=timeout_seconds,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[len("data: "):]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if "candidates" in data and data["candidates"]:
                            parts = data["candidates"][0].get("content", {}).get("parts", [])
                            for part in parts:
                                if "text" in part:
                                    yield part["text"]
                    except json.JSONDecodeError:
                        pass


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
