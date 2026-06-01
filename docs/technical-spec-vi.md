# Đặc Tả Kỹ Thuật MedChat Agent

## Mục Tiêu

MedChat Agent là backend FastAPI hỗ trợ hỏi đáp y tế/dược bằng mô hình RAG. Hệ thống ưu tiên bằng chứng từ Qdrant, có thể bổ sung web search, trích dẫn nguồn, chặn câu ngoài phạm vi và xử lý an toàn cho tình huống khẩn cấp.

## Kiến Trúc Chính

- `backend/main.py`: tạo FastAPI app và cấu hình logging cho `backend.*`, `core.*`.
- `backend/api/schemas.py`: định nghĩa request/response API.
- `backend/api/routes.py`: wiring service, Qdrant, model chat, embedding, web search.
- `core/chat_service.py`: điều phối safety, routing, retrieval, evidence gate, web fallback, LLM.
- `core/agent.py`: phân loại nhẹ intent/entity để hỗ trợ retrieval/rerank, không còn là nguồn query duy nhất.
- `core/retrieval.py`: truy vấn Qdrant, rerank bằng dense score, sparse score, field/entity/trust bonus.
- `core/web_sources.py`: search/fetch web nguồn trusted hoặc open.
- `core/llm.py`: adapter OpenAI, Gemini, fallback model và embedding local E5.

## Luồng Xử Lý `/chat`

1. `safety_precheck`: short-circuit nếu có dấu hiệu khẩn cấp.
2. `route_question`: lấy `intents`, `risk_level`, `entities`.
3. `build_retrieval_plan`: tạo plan hỗ trợ query/rerank.
4. Hybrid query: kết hợp câu hỏi gốc với query từ router.
5. Local Qdrant retrieval nếu `qdrant_search=true`.
6. `assess_evidence`: đánh giá `sufficient`, `partial`, `insufficient`.
7. Web retrieval nếu evidence yếu, nguồn quá hẹp, hoặc `force_web=true`.
8. Tạo citations, gọi LLM, kiểm tra citation bắt buộc.

## Retrieval Options

```json
{
  "allow_web": true,
  "force_web": false,
  "qdrant_search": true,
  "web_mode": "trusted",
  "max_sources": 8
}
```

- `allow_web`: cho phép web search.
- `force_web`: ép web search dù local evidence đủ.
- `qdrant_search`: bật/tắt Qdrant để test web-only.
- `web_mode`: `"trusted"` dùng whitelist; `"open"` lấy top search results không whitelist cứng.
- `max_sources`: số nguồn web tối đa, giới hạn 1-12 ở request và bị cap bởi config.

## Embedding Model

Embedding mặc định là `intfloat/multilingual-e5-base`, cấu hình bằng `EMBEDDING_MODEL`. Vector size trong Qdrant là `768` (`QDRANT_VECTOR_SIZE=768`) và collection mặc định là `pharmacy_chunks`.

`SentenceTransformerEmbeddingModel` chạy local qua `sentence-transformers`, ép HuggingFace offline bằng `TRANSFORMERS_OFFLINE=1` và `HF_HUB_OFFLINE=1`. Khi embed:
- Query dùng prefix `query: <text>`.
- Chunk/passage dùng prefix `passage: <text>`.
- Vector được normalize (`normalize_embeddings=True`) để phù hợp cosine distance.

## Chunk Và Ingestion

Dữ liệu ingest là các file JSON dạng array, đọc đệ quy từ thư mục chỉ định. Mỗi chunk cần có `text` và `metadata` với các trường bắt buộc: `name`, `source`, `type`, `field`, `chunk_index`.

Ví dụ:

```json
[
  {
    "text": "Hoạt chất: Abacavir | Phần: Chỉ định | Nội dung: Điều trị nhiễm HIV.",
    "metadata": {
      "name": "Abacavir",
      "id": "abacavir",
      "source": "Dược chất Long Châu",
      "type": "Dược chất",
      "field": "indication",
      "chunk_index": 0
    }
  }
]
```

`canonicalize_chunk` chuẩn hóa Unicode, sửa mojibake nếu đủ tin cậy, tạo `content_hash`, `source_slug`, `type_slug`, `trust_tier=local_curated`, `source_family`, `local_path` và ID ổn định bằng UUID5. Payload ghi vào Qdrant gồm `text`, `sparse_text` đã bỏ dấu, `entities`, metadata và `ingested_at`.

Ingestion tạo collection nếu chưa có, dùng cosine distance, tạo payload index cho `field`, `trust_tier`, `source_family`, `name`, embed theo batch (`INGESTION_BATCH_SIZE=64`) và bỏ qua point đã tồn tại theo ID.

## Retrieval Pipeline

Pipeline local retrieval:

1. `route_question` trích intent/entity/risk.
2. `build_retrieval_plan` tạo query mở rộng, metadata filters và preferred fields.
3. `chat_service` tạo hybrid query bằng câu hỏi gốc + query từ plan.
4. Embedding hybrid query với prefix `query:`.
5. `QdrantRetriever` gọi `query_points(limit=20, with_payload=True)`.
6. Nếu Qdrant báo thiếu payload index, retry không filter.
7. Convert point thành `EvidenceItem`, tính `sparse_score`, rồi rerank.
8. `assess_evidence` quyết định đủ/thiếu bằng chứng trước khi gọi LLM hoặc web fallback.

Nếu `qdrant_search=false`, bước Qdrant bị skip để test web-only. Nếu local evidence yếu hoặc `force_web=true`, hệ thống chạy web retrieval và merge evidence trước khi tạo citation.

## Rerank

Rerank không chỉ dựa vào dense score từ Qdrant. Công thức sắp xếp cộng thêm các tín hiệu:

- `dense score`: điểm vector similarity từ Qdrant.
- `sparse_score`: tỷ lệ term/entity trong query xuất hiện trong `text` sau khi bỏ dấu.
- `field_bonus=0.15`: nếu chunk thuộc field mong muốn, có alias như `dosage`, `indication`, `warning`, `contraindication`.
- `entity_bonus`: tối đa `0.25` theo mức khớp entity bắt buộc.
- `trust_bonus`: `regulatory=0.30`, `clinical_reference=0.20`, `local_curated=0.15`, `web_whitelisted=0.05`.

Sau rerank, evidence gate kiểm tra entity bắt buộc, intent được cover, và với câu rủi ro cao cần ít nhất hai nguồn khác nhau. Nếu `web_mode=open`, exact entity gate được nới lỏng cho web để tránh fail khi kết quả dùng alias/biệt dược khác.

## Web Search Modes

`trusted`:
- Search theo từng whitelist domain bằng `site:<domain> query`.
- Chỉ fetch URL thuộc whitelist trong `Settings.whitelist_domains`.
- Trust tier: `regulatory`, `clinical_reference`, hoặc `web_whitelisted`.

`open`:
- Search một lần bằng query gốc/hybrid.
- Fetch top results đến `max_sources`.
- Không yêu cầu whitelist, nhưng bỏ một số social domains phổ biến.
- Trust tier: `web_open`.
- Khi `web_mode=open`, exact entity gate được nới lỏng để tránh fail với biệt dược/alias chưa biết.

## LLM Fallback

`routes._build_chat_model` chọn:
- OpenAI nếu chỉ có `OPENAI_API_KEY`.
- Gemini nếu chỉ có `GEMINI_API_KEY`.
- `FallbackChatModel(OpenAI, Gemini)` nếu có cả hai. Mọi exception từ OpenAI sẽ chuyển sang Gemini.

Config chính:

```env
OPENAI_API_KEY=...
CHAT_MODEL=gpt-4.1-mini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
```

## Logging

Chạy:

```powershell
python -m uvicorn backend.main:app --reload --log-level info
```

Các log quan trọng:

- `chat.start`: flags request.
- `chat.route`: intents/entities/risk.
- `chat.retrieval_plan`: query, filters, broad filters.
- `chat.local_retrieval`: số chunk local và top titles.
- `chat.evidence`: status/reasons/warnings.
- `chat.web_retrieval`: start/skip/count/fail và reason.
- `retrieval.qdrant`: collection, filters, raw/ranked count.

## Ví Dụ Test Web Open

```json
{
  "message": "Hoạt chất Efferalgan",
  "retrieval_options": {
    "allow_web": true,
    "force_web": true,
    "qdrant_search": false,
    "web_mode": "open",
    "max_sources": 10
  }
}
```

Log mong đợi:

```text
chat.local_retrieval skipped reason=qdrant_search_disabled
chat.web_retrieval start ... reason=force_web
chat.web_retrieval count=...
```

## Kiểm Thử

Chạy toàn bộ:

```powershell
pytest
```

Các nhóm test chính:
- `tests/test_chat_service.py`: orchestration, fallback, web flags.
- `tests/test_web_sources.py`: search/fetch trusted/open.
- `tests/test_agent_safety.py`: routing, disease/symptom triage.
- `tests/test_retrieval.py`: Qdrant filter/rerank.
- `tests/test_ingestion.py`: canonicalize/index chunks.
