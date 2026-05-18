# Local E5 Qdrant Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build ingestion that embeds local JSON chunks with `intfloat/multilingual-e5-base` and upserts vectors plus payloads into Qdrant.

**Architecture:** Keep canonical chunk validation unchanged, add an async indexing path that batches chunks, calls an injected embedding model with E5 passage prefixes, ensures the Qdrant collection exists, and upserts points. Runtime chat/query embedding must use the same local E5 model with query prefixes.

**Tech Stack:** Python, pytest, qdrant-client, sentence-transformers, FastAPI.

---

### Task 1: Qdrant Ingestion Behavior

**Files:**
- Modify: `tests/test_ingestion.py`
- Modify: `core/ingestion.py`

- [ ] **Step 1: Write the failing test**

Add fake embedding and Qdrant clients, then assert `ingest_directory_async` embeds `passage:` text and upserts payloads containing `text`, `sparse_text`, `entities`, metadata, and `ingested_at`.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ingestion.py::test_ingest_directory_async_embeds_and_upserts_to_qdrant -v`
Expected: FAIL because `ingest_directory_async` does not exist.

- [ ] **Step 3: Write minimal implementation**

Add `ingest_directory_async`, `ensure_collection`, point payload construction, batching, and collection creation for cosine vectors.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ingestion.py::test_ingest_directory_async_embeds_and_upserts_to_qdrant -v`
Expected: PASS.

### Task 2: Local E5 Embedding Adapter

**Files:**
- Modify: `tests/test_chat_service.py`
- Modify: `core/llm.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Write the failing test**

Add a lightweight monkeypatched test proving `SentenceTransformerEmbeddingModel` prefixes query inputs with `query:` by default and passage inputs with `passage:` when requested.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_chat_service.py::test_sentence_transformer_embedding_model_uses_e5_prefixes -v`
Expected: FAIL because the adapter does not exist.

- [ ] **Step 3: Write minimal implementation**

Add lazy import of `sentence_transformers.SentenceTransformer`, normalize returned embeddings to plain `list[list[float]]`, and keep `FakeEmbeddingModel` unchanged.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_chat_service.py::test_sentence_transformer_embedding_model_uses_e5_prefixes -v`
Expected: PASS.

### Task 3: Wiring And Defaults

**Files:**
- Modify: `core/config.py`
- Modify: `core/cli.py`
- Modify: `backend/api/routes.py`
- Modify: `tests/test_chat_service.py`

- [ ] **Step 1: Write failing wiring tests**

Update service factory tests to expect `SentenceTransformerEmbeddingModel` and verify defaults are `intfloat/multilingual-e5-base` and vector size `768`.

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_chat_service.py tests/test_ingestion.py -v`
Expected: FAIL on old OpenAI embedding wiring or old config defaults.

- [ ] **Step 3: Implement wiring**

Use `asyncio.run` in CLI, use async ingestion in API endpoint, and instantiate local E5 embedding model in service factory.

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_chat_service.py tests/test_ingestion.py -v`
Expected: PASS.

### Task 4: Full Verification

**Files:**
- No additional edits expected.

- [ ] **Step 1: Run full test suite**

Run: `pytest -q`
Expected: all tests pass.

- [ ] **Step 2: Report exact verification result**

Final response must include the exact test command run and any remaining runtime requirement, especially that Qdrant must be reachable for real ingestion.
