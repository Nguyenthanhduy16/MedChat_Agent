# Pharmacy AI Chatbot Agent Design

Date: 2026-05-16

## Goal

Build an MVP backend for a specialized pharmacy AI chatbot agent. The system answers drug-related questions in Vietnamese, retrieves evidence from a curated pharmacy knowledge base, cites specific sources, reasons over user context, and clearly separates reference information from professional medical advice.

The MVP targets both general users and pharmacy learners/professionals. It defaults to safe, plain-language answers for general users, while allowing more technical explanations when the question asks for them and evidence is available.

## Current Project Context

The repository currently contains empty `backend` and `core` directories, an empty `.env`, an empty `requirements.txt`, and a large local JSON chunk corpus under `data/chunks`.

The local corpus includes:

- `longchau_ingredients_chunked`: ingredient and active substance chunks.
- `thuoc_long_chau_chunked`: Long Chau drug/product chunks.
- `tpcn_longchau_chunked`: supplement/product chunks.
- `pharmacity_chunked`: disease and health topic chunks.

Some inspected JSON text appears to have mojibake or encoding corruption. The ingestion design must validate and normalize text before embedding. Chunks that cannot be repaired should be reported and skipped rather than silently indexed.

The workspace is not currently a git repository, so this spec cannot be committed until git is initialized or the project is placed inside a repository.

## Scope

The selected scope is an MVP backend, not a full-stack product.

In scope:

- FastAPI backend.
- Provider-agnostic model adapters.
- Default OpenAI-compatible implementation for chat and embeddings.
- Qdrant vector storage for embeddings and metadata.
- Local JSON corpus ingestion.
- Runtime hybrid retrieval from local Qdrant.
- Whitelisted web source retrieval for approved medical/pharmacy sources.
- Multi-label intent classification with risk level.
- Safety guardrails before and after generation.
- Source citations in structured responses.
- Focused unit and integration tests.

Out of scope for this MVP:

- User authentication.
- Production audit logging and monitoring.
- Full web UI.
- Automated continuous source crawling.
- Open internet search without whitelist controls.
- Clinical decision support, diagnosis, prescription, or personalized treatment decisions.

## Selected Approach

Use a hybrid architecture: deterministic RAG core plus a thin agent router.

The router classifies the user request and chooses controlled retrieval paths. The RAG and safety behavior remain explicit and testable. The LLM synthesizes answers only from assembled evidence and must not produce unsupported drug claims.

This balances flexibility with safety. A free-form agent is too risky for pharmacy use, while a single linear RAG chain is too limited for multi-intent questions such as drug interactions with disease context.

## Architecture

The backend has five layers:

1. API layer: FastAPI routes, request validation, response schemas, health checks, ingestion/reindex endpoints, and source status endpoints.
2. Agent router layer: multi-label intent classification, risk level assignment, audience detection, and retrieval plan construction.
3. Evidence layer: Qdrant hybrid retrieval from local JSON chunks plus optional whitelisted web source retrieval.
4. Answer generation layer: provider-agnostic LLM and embedding adapters, with OpenAI as the default implementation.
5. Safety and citation layer: pre-checks, post-checks, citation formatting, and fail-closed behavior for unsupported or high-risk answers.

General request flow:

```text
User question
 -> request validation and normalization
 -> safety pre-check
 -> multi-label router + risk level
 -> local Qdrant retrieval
 -> optional whitelist web retrieval
 -> hybrid evidence retrieval, sufficiency gate, and citation package
 -> grounded answer generation
 -> safety post-check and citation completeness check
 -> structured JSON response
```

## Components

### `backend/api`

FastAPI routes and schemas.

Initial routes:

- `GET /health`: service health.
- `POST /chat`: chat request and structured answer.
- `POST /ingest`: ingest or reindex local JSON chunks.
- `GET /sources/status`: report indexed source families and collection status.

### `core/config`

Reads `.env` and centralizes settings:

- LLM provider and model.
- Embedding provider and model.
- Qdrant URL, API key, collection name, vector size, and distance metric.
- Web source whitelist.
- Retrieval top-k settings.
- Safety thresholds.
- Timeout and limit defaults for API, LLM, Qdrant, web retrieval, and ingestion.

### `core/llm`

Provider-agnostic interfaces:

- `ChatModel.generate(messages, options)`.
- `EmbeddingModel.embed(texts)`.

The default implementation should support OpenAI-compatible chat and embedding APIs. The interface should allow later local or alternative providers without changing retrieval, safety, or API modules.

### `core/ingestion`

Responsibilities:

- Discover JSON files under `data/chunks`.
- Identify source family from path.
- Load chunk arrays.
- Normalize or repair text encoding when possible.
- Validate required metadata.
- Enrich metadata.
- Generate stable document and chunk IDs.
- Embed text.
- Upsert vectors and payloads into Qdrant.
- Write an ingestion report.

Required Qdrant payload metadata:

- `source`
- `url`
- `type`
- `name`
- `field`
- `chunk_index`
- `source_family`
- `local_path`
- `trust_tier`
- `ingested_at`

### Input Chunk JSON Schema

Each source JSON file is expected to contain an array of chunk objects. The ingestion layer should accept the current local corpus shape and normalize it into a canonical internal document.

Minimum accepted chunk shape:

```json
{
  "text": "Hoạt chất: Abacavir | Phần: Chỉ định | Nội dung: ...",
  "metadata": {
    "name": "Abacavir",
    "id": "abacavir",
    "url": "https://nhathuoclongchau.com.vn/thanh-phan/abacavir",
    "category": "Dược chất LC",
    "type": "Dược chất",
    "source": "Dược chất Long Châu",
    "original_lang": "vietnamese",
    "field": "indication",
    "chunk_index": 0
  }
}
```

Required fields after normalization:

- `text`: non-empty normalized UTF-8 text.
- `metadata.name`: display name for the drug, ingredient, product, disease, or topic.
- `metadata.url`: source URL when available.
- `metadata.source`: human-readable source name.
- `metadata.type`: source content type.
- `metadata.field`: section or field represented by the chunk.
- `metadata.chunk_index`: source-local chunk index.

Optional input metadata may include `id`, `category`, `original_lang`, `source_family`, `title`, `published_at`, and `retrieved_at`.

Canonical internal chunk:

```json
{
  "id": "sha256:...",
  "text": "...",
  "entities": {
    "drugs": ["abacavir"],
    "ingredients": ["abacavir"],
    "conditions": []
  },
  "metadata": {
    "source": "Dược chất Long Châu",
    "source_family": "longchau_ingredients_chunked",
    "trust_tier": "local_curated",
    "url": "https://nhathuoclongchau.com.vn/thanh-phan/abacavir",
    "type": "Dược chất",
    "name": "Abacavir",
    "field": "indication",
    "chunk_index": 0,
    "local_path": "data/chunks/longchau_ingredients_chunked/abacavir.json",
    "content_hash": "sha256:...",
    "ingested_at": "2026-05-17T00:00:00Z"
  }
}
```

### Stable ID Strategy

Stable IDs must not depend on ingestion order.

Chunk ID input:

```text
source_family + normalized_local_path + metadata.id_or_slug + field + chunk_index + normalized_text_hash
```

Rules:

- `normalized_local_path` uses forward slashes and is relative to the project root.
- `metadata.id_or_slug` uses `metadata.id` when present, otherwise a slugified `metadata.name`.
- `normalized_text_hash` is SHA-256 over normalized text after encoding repair, Unicode normalization, whitespace collapse, and trimming.
- Final Qdrant point ID is a deterministic UUIDv5 or SHA-256-derived hex string from the full input.
- Re-ingesting unchanged chunks should upsert the same IDs.
- If the source text changes, the chunk receives a new ID and the old ID should be removed during a full reindex or marked stale during incremental indexing.

### Multilingual And Encoding Strategy

The MVP primarily answers Vietnamese questions, but source names, active ingredients, and regulatory sources may be Vietnamese or English.

Encoding and language handling:

- Read files as UTF-8 first.
- Detect mojibake patterns such as `Ã`, `Ä`, `á»`, and replacement characters.
- Attempt deterministic repair for common UTF-8-as-Latin-1 corruption.
- Normalize repaired text with Unicode NFC.
- Preserve Vietnamese diacritics for display and answer generation.
- Store an additional accent-folded/search-normalized text field for sparse matching.
- Keep original text in ingestion reports when repair changes content materially.
- If repair confidence is low, skip the chunk and report it rather than indexing corrupted text.
- Entity extraction should use both original and accent-folded forms so queries with and without Vietnamese diacritics can match.
- English source content from whitelist domains is allowed. The answer generator should summarize it in Vietnamese unless the user asks otherwise.

### `core/retrieval`

Responsibilities:

- Query Qdrant with hybrid search: dense vector similarity plus sparse keyword/entity matching.
- Extract drug names, active ingredients, dose terms, route terms, disease terms, and safety keywords for sparse matching.
- Apply metadata filters based on intent, risk, source family, field, and trust tier.
- Retrieve top-k per intent rather than one global top-k.
- Rerank with a score combining dense similarity, sparse/entity match score, metadata relevance, trust tier, field relevance, source recency when available, and duplicate penalties.
- Dedupe repeated URLs and near-duplicate snippets.

Hybrid retrieval is required because pharmacy questions often depend on exact entity matches. Dense embedding search alone may miss or blur drug names, ingredient names, contraindication keywords, and interaction pairs.

### `core/evidence`

Responsibilities:

- Build an evidence package from local and whitelisted web retrieval results.
- Run an Evidence Sufficiency Gate before answer generation.
- Return `evidence_status`, warnings, and reasons when evidence is incomplete.
- Prevent grounded answer generation when evidence is too weak for the requested risk level.

Evidence status values:

- `sufficient`: enough relevant evidence exists for the main intents and risk level.
- `partial`: evidence covers some intents or claims, but important gaps remain.
- `insufficient`: evidence is missing, too weak, or not relevant enough.
- `conflicting`: relevant sources disagree on a material point.

The sufficiency gate considers:

- Coverage of all high-priority intents.
- Minimum number of distinct sources for `high` risk answers when available.
- Exact entity coverage for named drugs, active ingredients, and interaction pairs.
- Retrieval score thresholds from dense and sparse search.
- Trust tier and source type.
- Whether the answer would require personal medical advice.

If status is `insufficient`, the system must not generate unsupported pharmacy claims. If status is `partial` or `conflicting`, the response must include warnings and use limited, conditional language.

### `core/web_sources`

Whitelisted source retrieval only.

Approved source policy:

- Query only configured domains.
- Capture title, URL, snippet, source name, retrieval time, and date when available.
- Mark web evidence with trust tier.
- Merge with local evidence.
- Optionally cache approved fetched chunks into Qdrant in a later iteration.

The MVP must not perform unrestricted web search for pharmacy answers.

Web source mechanism:

1. Router marks a question as needing web evidence when local evidence is `partial` or `insufficient`, when the user asks for current/regulatory information, or when the local corpus does not cover a high-priority intent.
2. `core/web_sources` selects candidate domains from the whitelist by intent and jurisdiction.
3. The adapter builds domain-scoped queries such as `site:dailymed.nlm.nih.gov warfarin ibuprofen interaction`.
4. The whitelist is enforced before search and again before fetch. URLs outside configured domains are discarded even if returned by the search provider.
5. Fetching extracts title, canonical URL, publication or revision date when available, visible text snippet, and source organization.
6. Extracted snippets are normalized into the same evidence package format as local chunks.
7. Evidence is ranked with trust tier, exact entity coverage, recency when relevant, and source type.
8. The answer must cite the fetched source URL directly, not the search result page.

Initial trust tiers:

- `regulatory`: official regulators and labels such as FDA, DailyMed, EMA, and Ministry of Health domains.
- `clinical_reference`: WHO, PubMed abstracts, and other approved clinical reference domains.
- `local_curated`: local JSON corpus from approved pharmacy source datasets.
- `web_whitelisted`: approved web source that does not fit a higher tier.

### `core/agent`

Thin orchestration layer.

The router returns:

```json
{
  "intents": ["dosage", "interaction", "contraindication"],
  "risk_level": "high",
  "audience": "general",
  "needs_context": true
}
```

MVP intent labels:

- `drug_identity`: names, active ingredients, formulations, components.
- `indication`: indications and uses.
- `dosage`: dose, administration, missed dose, overdose.
- `contraindication`: contraindications and precautions.
- `interaction`: drug-drug, drug-food, and drug-condition interactions.
- `adverse_effect`: side effects and danger signs.
- `pregnancy_lactation`: pregnancy and breastfeeding.
- `pediatric_elderly`: children and older adults.
- `disease_context`: disease background or symptom context.
- `general_health`: general health knowledge.
- `emergency`: emergency symptoms, poisoning, severe overdose, anaphylaxis.
- `unsupported`: outside scope or insufficient evidence.

Risk levels:

- `low`: general identity or use questions with no personalization.
- `medium`: general dose, side effects, or non-urgent disease context.
- `high`: interactions, contraindications, pregnancy, children, older adults, serious comorbidities, or unclear overdose.
- `urgent`: emergency symptoms, anaphylaxis, poisoning, severe overdose, chest pain, severe breathing difficulty, seizures, loss of consciousness, or self-harm risk.

### `core/safety`

Safety behavior is applied before retrieval and after generation.

Policy by risk level:

- `low`: answer factual questions with citations.
- `medium`: answer with citations and include conditional warnings.
- `high`: avoid personalized medical decisions, ask for missing context when needed, and recommend consulting a doctor or pharmacist.
- `urgent`: prioritize emergency guidance; do not produce a long RAG answer or dosing analysis.

The system must not diagnose, prescribe, tell a user to start or stop medication for a personal case, or recommend changing a dose without professional supervision.

### `core/citations`

Responsibilities:

- Convert evidence into citation IDs such as `S1`, `S2`.
- Dedupe sources by URL and local source identity.
- Keep snippets short and traceable.
- Ensure factual pharmacy claims have citations.
- Trigger one regeneration attempt if citation completeness fails.
- Return a limited answer if citation completeness still fails.

## Confidence Definition

`confidence` is an operational confidence label for the response, not a probability and not medical certainty.

Allowed values:

- `high`: evidence status is `sufficient`, retrieved sources are relevant to all main intents, named drug/entity coverage is exact, and no material conflict is detected.
- `medium`: evidence status is `sufficient` or `partial`, core claims have citations, but some context is missing, source coverage is narrow, or the question has moderate risk.
- `low`: evidence status is `partial`, `insufficient`, or `conflicting`; retrieval scores are weak; source coverage is incomplete; or the question is high risk and lacks user context.

`urgent` safety responses should usually use `low` or `medium` confidence unless the answer is limited to emergency escalation guidance.

Urgent confidence clarification:

- Use `medium` only when the system is confident the request contains urgent danger signs and the response is limited to emergency escalation guidance.
- Use `low` when the urgent classification depends on ambiguous wording, missing context, uncertain substance identity, or conflicting evidence.
- Never use `high` for urgent personal medical scenarios, because the system is not making a clinical diagnosis or treatment decision.

## API Request And Response

### `POST /chat` Request Schema

```json
{
  "message": "Tôi đang uống warfarin, có dùng ibuprofen được không?",
  "conversation_id": "optional-session-id",
  "user_context": {
    "age": 67,
    "sex": "female",
    "pregnancy_status": "not_pregnant",
    "lactation": false,
    "conditions": ["rung nhĩ"],
    "current_medications": ["warfarin"],
    "allergies": [],
    "location": "VN"
  },
  "preferences": {
    "language": "vi",
    "audience": "general",
    "include_technical_detail": false
  },
  "retrieval_options": {
    "allow_web": true,
    "max_sources": 8
  }
}
```

Request fields:

- `message` is required, must be non-empty, and should be capped by configuration.
- `conversation_id` is optional and used only for contextual continuity. MVP may treat it as client-provided state without persistent chat history.
- `user_context` is optional. It must be used to raise risk and ask for missing context, not to produce personalized prescriptions.
- `preferences.language` defaults to `vi`.
- `preferences.audience` defaults to `general` and may be `general` or `professional`.
- `retrieval_options.allow_web` defaults to the server setting and must never bypass the whitelist.
- `retrieval_options.max_sources` is bounded by server configuration.

Allowed `pregnancy_status` values:

- `unknown`
- `not_pregnant`
- `pregnant`
- `planning_pregnancy`

### `POST /chat` Response Schema

`POST /chat` should return structured JSON:

```json
{
  "answer": "...",
  "safety_notice": "...",
  "citations": [
    {
      "id": "S1",
      "title": "Abacavir - Long Chau",
      "url": "https://nhathuoclongchau.com.vn/thanh-phan/abacavir",
      "source": "Duoc chat Long Chau",
      "trust_tier": "local_curated",
      "snippet": "..."
    }
  ],
  "intents": ["dosage", "interaction"],
  "risk_level": "high",
  "evidence_status": "partial",
  "warnings": [
    "Evidence covers the interaction risk but does not include the patient's full medication list."
  ],
  "confidence": "medium",
  "requires_professional_advice": true
}
```

## Data Flow

### Chat Flow

```text
POST /chat
 -> validate request
 -> normalize question
 -> safety pre-check
 -> multi-label router + risk level
 -> if urgent: emergency response template + optional citations
 -> build retrieval plan from intents and risk
 -> query Qdrant with dense vector + sparse keyword/entity matching + metadata filters
 -> if evidence is insufficient and policy allows: whitelist web search
 -> rank and dedupe evidence
 -> Evidence Sufficiency Gate
 -> if insufficient: limited response with evidence_status and warnings
 -> assemble grounded context
 -> generate answer through provider adapter
 -> citation completeness check
 -> safety post-check
 -> return structured response
```

Example retrieval plan for: "Mẹ tôi đang dùng warfarin, có uống ibuprofen được không?"

```json
{
  "intents": ["interaction", "contraindication", "adverse_effect"],
  "risk_level": "high",
  "entities": {
    "drugs": ["warfarin", "ibuprofen"],
    "interaction_pairs": [["warfarin", "ibuprofen"]]
  },
  "queries": [
    {
      "query": "warfarin ibuprofen tuong tac",
      "field_boost": ["interaction", "warning"]
    },
    {
      "query": "ibuprofen chong chi dinh than trong xuat huyet",
      "field_boost": ["contraindication", "adverse_effect"]
    },
    {
      "query": "warfarin thuoc chong dong NSAID",
      "field_boost": ["interaction"]
    }
  ],
  "metadata_filters": {
    "field": ["interaction", "contraindication", "adverse_effect", "warning"],
    "trust_tier": ["regulatory", "clinical_reference", "local_curated"]
  }
}
```

### Ingestion Flow

```text
JSON files in data/chunks
 -> discover source family
 -> load JSON
 -> normalize or repair text encoding when possible
 -> validate required fields
 -> extract entities and accent-folded sparse terms
 -> enrich metadata: trust_tier, local_path, source_family
 -> compute stable document and chunk ID
 -> embed text
 -> upsert vectors and payload into Qdrant
 -> write ingest report
```

### Whitelist Web Flow

```text
Need extra evidence
 -> select allowed source domains by intent
 -> build domain-scoped search query
 -> enforce whitelist before search and fetch
 -> search or fetch only whitelisted sources
 -> extract title, URL, snippet, and date when available
 -> normalize snippet and entity terms
 -> classify trust_tier
 -> optionally embed/cache fetched chunks into Qdrant later
 -> merge with local evidence
```

## Contextual Reasoning

Contextual reasoning is implemented by retrieval planning and answer constraints, not by allowing the model to freely infer medical decisions.

If the question includes age, pregnancy, lactation, comorbidities, current medications, allergies, symptoms, route of administration, dose, or timing, the router should raise risk when appropriate and request evidence for each relevant intent.

If critical context is missing for a high-risk question, the answer should say what information is missing and recommend professional consultation rather than giving a definitive personal recommendation.

## Error Handling

The system should fail closed for medical content.

Cases:

- No evidence found: explain that there is insufficient evidence in the configured sources and avoid unsupported claims.
- Conflicting evidence: disclose that sources differ, prefer higher trust tier sources, and avoid action-specific advice.
- Evidence Sufficiency Gate failure: return `evidence_status` as `partial`, `insufficient`, or `conflicting`; include `warnings`; do not generate a definitive pharmacy recommendation.
- Qdrant unavailable: return a structured error; do not fallback to LLM-only pharmacy answers.
- LLM provider unavailable: return a friendly structured error while preserving correlation metadata.
- Whitelist web retrieval unavailable: answer from local evidence if sufficient; otherwise report insufficient updated evidence.
- Ingestion encoding failure: record in the ingestion report and skip unrepaired chunks.
- Missing citation after generation: regenerate once; if still missing, return a limited response with a citation warning.

## Safety Requirements

Every pharmacy answer must:

- Include a separate `safety_notice`.
- Include citations for key factual drug claims.
- State that the answer is reference information and not a substitute for medical advice.
- Avoid diagnosis, prescribing, and personalized dose changes.
- Escalate urgent symptoms to emergency care.

Urgent examples:

- Severe allergic reaction or anaphylaxis.
- Severe shortness of breath.
- Chest pain.
- Seizure.
- Loss of consciousness.
- Serious overdose or poisoning.
- Self-harm intent.

For urgent cases, the response should be short and action-oriented, prioritizing emergency care over detailed drug explanation.

## Testing

### Unit Tests

- Router returns multiple intents for multi-topic questions.
- Risk level increases for pregnancy, pediatric use, elderly use, interactions, contraindications, overdose, and emergency symptoms.
- `POST /chat` request validation accepts optional context and rejects empty or oversized messages.
- Input chunk schema validation accepts the current local corpus shape and rejects missing text or unusable metadata.
- Stable ID generation returns the same ID for unchanged chunks and a different ID when normalized text changes.
- Encoding repair preserves valid Vietnamese text, repairs common mojibake, and skips low-confidence repairs.
- Retrieval combines dense vector matching, sparse keyword/entity matching, metadata filtering, and reranking signals.
- Evidence Sufficiency Gate returns `sufficient`, `partial`, `insufficient`, and `conflicting` for representative evidence packages.
- Confidence labels follow the defined evidence, entity coverage, conflict, and risk rules.
- Urgent responses never return `high` confidence for personal medical scenarios.
- Citation formatter deduplicates URLs and generates stable IDs.
- Safety post-check blocks unsupported pharmacy claims without citations.
- Ingestion generates stable IDs and required metadata.
- Encoding normalization identifies and reports unrepaired chunks.

### Integration Tests

- Ingest a small JSON fixture into a Qdrant test collection.
- Retrieve evidence for `drug_identity`, `interaction`, and `contraindication`.
- `POST /chat` returns the expected schema with mocked LLM output.
- Qdrant unavailable prevents LLM-only drug answers.
- Whitelist web retrieval is called only for approved domains.
- Responses include `evidence_status` and `warnings` when evidence is partial, insufficient, or conflicting.
- Web retrieval enforces whitelist before search and fetch, cites fetched source URLs, and respects timeout defaults.
- Timeout paths return structured errors or limited responses without falling back to unsupported LLM-only drug answers.

### Golden Cases

- "Paracetamol dùng để làm gì?"
- "Tôi đang uống warfarin, có dùng ibuprofen được không?"
- "Phụ nữ mang thai dùng isotretinoin được không?"
- "Tôi uống quá liều thuốc X và đang khó thở"
- "So sánh amoxicillin và azithromycin"
- "Cho tôi đơn thuốc trị viêm họng"
- "Aspirin có dùng được cho trẻ em bị sốt không?"
- "Metformin có cần lưu ý gì nếu người bệnh suy thận?"
- "Tôi đang cho con bú, có dùng loratadin được không?"

### Manual Evaluation Checklist

- Citations are specific and verifiable.
- The answer avoids replacing a doctor or pharmacist.
- The default language is understandable for general Vietnamese users.
- Technical questions can receive structured professional detail when evidence supports it.
- The system says when data is insufficient.

## Implementation Defaults

The implementation plan should use these defaults unless a later review changes them:

- Model names are environment-configured. The spec requires OpenAI-compatible chat and embedding adapters but does not hard-code model IDs.
- Qdrant defaults to `http://localhost:6333` with collection name configured through `.env`.
- Local development assumes Qdrant can run through Docker or an existing local Qdrant service.
- Initial whitelist domains are `moh.gov.vn`, `who.int`, `fda.gov`, `accessdata.fda.gov`, `dailymed.nlm.nih.gov`, `ema.europa.eu`, `medicines.org.uk`, and `pubmed.ncbi.nlm.nih.gov`.
- The web source adapter is environment-configured and must enforce the whitelist before any request is made.
- Add a minimal ingestion CLI in addition to the `POST /ingest` endpoint, because local corpus indexing is a developer workflow.
- Development logs may include request IDs, intents, risk levels, retrieval counts, source IDs, and errors. They must not log raw personal health details by default.

Default timeouts and limits:

- API request body size: 64 KB.
- Chat request end-to-end timeout: 60 seconds.
- LLM generation timeout: 30 seconds.
- Embedding batch timeout: 60 seconds.
- Qdrant query timeout: 5 seconds per retrieval call.
- Qdrant upsert timeout: 30 seconds per batch.
- Whitelist web search timeout: 8 seconds.
- Web fetch timeout: 5 seconds per URL.
- Maximum fetched web URLs per chat request: 5.
- Maximum total evidence chunks sent to the LLM: 12.
- Default local retrieval top-k per intent: 6 before reranking.
- Default final citations returned: 3 to 8 depending on evidence coverage.
- Ingestion batch size: 64 chunks per embedding/upsert batch unless provider limits require less.
