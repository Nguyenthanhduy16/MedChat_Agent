import argparse
import asyncio
import json
from pathlib import Path

from qdrant_client import AsyncQdrantClient

from core.config import get_settings
from core.ingestion import ingest_directory_async
from core.llm import SentenceTransformerEmbeddingModel


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest pharmacy JSON chunks.")
    parser.add_argument("--path", default="data/chunks", help="Path containing JSON chunk files.")
    args = parser.parse_args()
    settings = get_settings()
    qdrant_client = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        check_compatibility=False,
        timeout=settings.qdrant_upsert_timeout_seconds,
    )
    report = asyncio.run(
        ingest_directory_async(
            Path(args.path),
            embedding_model=SentenceTransformerEmbeddingModel(model=settings.embedding_model),
            qdrant_client=qdrant_client,
            settings=settings,
        )
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
