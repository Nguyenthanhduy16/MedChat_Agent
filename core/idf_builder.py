import json
import math
from collections import Counter
from pathlib import Path

from core.sparse_vectors import tokenize_sparse

def build_idf_weights(chunk_dir: Path, output_file: Path) -> dict[str, float]:
    """
    Scans JSON chunk files in the directory, counts document frequencies (DF),
    and computes BM25 IDF for each token.
    Saves to output_file and returns the dictionary.
    """
    if not chunk_dir.exists():
        return {}

    total_docs = 0
    df_counter: Counter[str] = Counter()

    for chunk_file in chunk_dir.rglob("*.json"):
        try:
            raw_json = chunk_file.read_text(encoding="utf-8")
            payload = json.loads(raw_json)
        except Exception:
            continue
            
        if not isinstance(payload, list):
            continue
            
        for chunk_data in payload:
            text = chunk_data.get("text", "")
            if not isinstance(text, str) or not text.strip():
                continue
            
            # Count unique tokens in this document
            tokens = set(tokenize_sparse(text))
            df_counter.update(tokens)
            total_docs += 1

    idf_weights = {}
    if total_docs > 0:
        for token, df in df_counter.items():
            # Standard Okapi BM25 IDF formula
            idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1.0)
            if idf > 0:
                idf_weights[token] = idf

    # Save to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(idf_weights, f, ensure_ascii=False, indent=2)

    return idf_weights
