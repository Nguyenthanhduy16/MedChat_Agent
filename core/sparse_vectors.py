from collections import Counter

from qdrant_client.http.models import SparseVector

from core.text import accent_fold


def build_sparse_vector(text: str) -> SparseVector:
    tokens = [token for token in accent_fold(text).split() if token]
    if not tokens:
        return SparseVector(indices=[], values=[])

    counts = Counter(tokens)
    max_count = max(counts.values())
    entries = sorted((_token_index(token), count / max_count) for token, count in counts.items())
    return SparseVector(
        indices=[index for index, _ in entries],
        values=[float(round(weight, 6)) for _, weight in entries],
    )


def _token_index(token: str) -> int:
    # FNV-1a 32-bit gives stable sparse dimensions without an external sparse model dependency.
    value = 2166136261
    for byte in token.encode("utf-8"):
        value ^= byte
        value = (value * 16777619) & 0xFFFFFFFF
    return max(1, value)
