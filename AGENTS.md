# Repository Guidelines

## Project Structure & Module Organization

This is a Python FastAPI backend for a pharmacy-focused medical chat agent.
Core domain logic lives in `core/`: chat orchestration, retrieval, ingestion, citations, safety, LLM adapters, and configuration. API entry points live in `backend/`, with `backend/main.py` creating the FastAPI app and `backend/api/` containing routes and Pydantic schemas. Tests live in `tests/`, with sample JSON fixtures under `tests/fixtures/`. Runtime/source data belongs in `data/`, and design or planning notes belong in `docs/`.

## Build, Test, and Development Commands

Create and activate a virtual environment before installing dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the API locally:

```powershell
uvicorn backend.main:app --reload
```

Run all tests:

```powershell
pytest
```

Run targeted tests while iterating:

```powershell
pytest tests/test_chat_service.py
pytest tests/test_retrieval.py -k qdrant
```

Ingest JSON chunks into Qdrant:

```powershell
python -m core.cli --path data/chunks
```

## Coding Style & Naming Conventions

Use Python 3.11+ style with type hints where practical. Follow the existing 4-space indentation, small module functions, and explicit dependency injection used in `core/chat_service.py` and `backend/api/routes.py`. Prefer `snake_case` for functions, variables, files, and test names; use `PascalCase` for classes and Pydantic models. Keep API schemas in `backend/api/schemas.py` and domain models in `core/models.py`.

## Testing Guidelines

The project uses `pytest` and `pytest-asyncio`; `pytest.ini` sets `pythonpath = .`. Name tests `test_*.py` and test functions `test_<behavior>()`. Prefer fakes and monkeypatching over live OpenAI, Qdrant, or web calls. Add or update tests whenever behavior changes in chat routing, retrieval, ingestion, citation handling, or safety checks.

## Commit & Pull Request Guidelines

Recent commits use short imperative summaries such as `add web_search` and `improve retrieval`. Keep commit subjects concise and behavior-focused. Pull requests should include a summary of user-visible changes, tests run, configuration or migration notes, and linked issues when applicable. Include API examples or screenshots only when response shapes or UI-facing behavior changes.

## Security & Configuration Tips

Configuration is loaded from `.env` through `core/config.py`. Do not commit real API keys or private endpoints. Key settings include `OPENAI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, `WEB_SEARCH_PROVIDER`, `WEB_SEARCH_ENDPOINT`, and `WEB_SEARCH_API_KEY`. Keep web retrieval constrained to trusted medical domains by updating `whitelist_domains` deliberately and with tests.
