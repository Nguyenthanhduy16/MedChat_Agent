from collections import Counter
import re

from qdrant_client.http.models import SparseVector

from core.text import accent_fold


BM25_K1 = 1.2
SPARSE_TOKEN_STOPWORDS = {
    "thuoc",
    "nho",
    "mat",
    "dung",
    "dich",
    "vien",
    "siro",
    "chai",
    "hop",
    "duoc",
}
SPARSE_TOKEN_STOP_PATTERNS = (
    re.compile(r"^\d+(?:\.\d+)?(?:mg|mcg|g|kg|ml|l|iu|ui|%)$"),
    re.compile(r"^\d+x\d+$"),
    re.compile(r"^\d+(?:v|vien|goi|ong|lo|chai|hop)$"),
    re.compile(r"^(?:mg|mcg|g|kg|ml|l|iu|ui)$"),
)

import json
from pathlib import Path

_IDF_WEIGHTS: dict[str, float] | None = None
_IDF_FILE = Path("data/idf_weights.json")

def _get_idf_weight(token: str) -> float:
    global _IDF_WEIGHTS
    if _IDF_WEIGHTS is None:
        try:
            if _IDF_FILE.exists():
                with open(_IDF_FILE, "r", encoding="utf-8") as f:
                    _IDF_WEIGHTS = json.load(f)
            else:
                _IDF_WEIGHTS = {}
        except Exception:
            _IDF_WEIGHTS = {}
    return _IDF_WEIGHTS.get(token, 1.0)

def tokenize_sparse(text: str) -> list[str]:
    return [token for token in accent_fold(text).split() if _is_sparse_token(token)]


def build_sparse_vector(text: str) -> SparseVector:
    tokens = tokenize_sparse(text)
    if not tokens:
        return SparseVector(indices=[], values=[])

    counts = Counter(tokens)
    index_weights: Counter[int] = Counter()
    for token, count in counts.items():
        tf_weight = _bm25_tf_weight(count)
        idf_weight = _get_idf_weight(token)
        index_weights[_token_index(token)] += tf_weight * idf_weight

    entries = sorted(index_weights.items())
    return SparseVector(
        indices=[index for index, _ in entries],
        values=[float(round(weight, 6)) for _, weight in entries],
    )


def _is_sparse_token(token: str) -> bool:
    return (
        len(token) >= 2
        and token not in SPARSE_TOKEN_STOPWORDS
        and not token.isdigit()
        and not any(pattern.match(token) for pattern in SPARSE_TOKEN_STOP_PATTERNS)
    )


def _bm25_tf_weight(term_frequency: int) -> float:
    return (term_frequency * (BM25_K1 + 1.0)) / (term_frequency + BM25_K1)


def _token_index(token: str) -> int:
    # FNV-1a 32-bit gives stable sparse dimensions without an external sparse model dependency.
    value = 2166136261
    for byte in token.encode("utf-8"):
        value ^= byte
        value = (value * 16777619) & 0xFFFFFFFF
    return max(1, value)
