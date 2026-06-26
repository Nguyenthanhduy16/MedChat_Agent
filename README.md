# MedChat Agent

Chatbot tư vấn dược phẩm AI, kết hợp RAG pipeline từ kho kiến thức y tế với giao diện web đầy đủ, hỗ trợ tiếng Việt, có guardrails an toàn và trích dẫn nguồn.

---

## Tính năng chính

| Tính năng | Mô tả |
|---|---|
| **Tư vấn y tế** | Trả lời câu hỏi về thuốc, liều dùng, tương tác, chống chỉ định bằng tiếng Việt với trích dẫn nguồn |
| **Safety guardrails** | Phát hiện tình huống khẩn cấp, phân loại rủi ro (low / medium / high / urgent), từ chối câu hỏi ngoài phạm vi y tế |
| **Hybrid retrieval** | Kết hợp dense vector search (Qdrant E5) và sparse keyword BM25, reranking theo trust tier |
| **Evidence gating** | 5 trạng thái coverage (complete / usable_partial / weak_partial / insufficient / conflicting) |
| **Web retrieval** | Tìm kiếm bổ sung từ danh sách domain y tế uy tín (FDA, WHO, MOH VN, Vinmec...) |
| **Multi-intent routing** | Phân loại đồng thời nhiều intent, xây retrieval plan riêng cho từng intent |
| **Streaming** | Trả kết quả từng token qua Server-Sent Events (`/chat/stream`) |
| **Citation management** | Tự động dedup, gán trust tier, format trích dẫn theo nguồn |

---

## Tech Stack

| Layer | Công nghệ |
|---|---|
| **Frontend** | React 19, Vite 8, TailwindCSS 4, Axios, react-markdown |
| **Backend API** | FastAPI 0.111+, Uvicorn, Python 3.11+ |
| **LLM** | OpenAI GPT-4o-mini (primary), Google Gemini 2.5 Flash (fallback), DeepSeek (optional) |
| **Embedding** | `intfloat/multilingual-e5-base` — chạy local, offline sau lần tải đầu |
| **Vector DB** | Qdrant — hybrid dense + sparse (RRF fusion) |
| **Reranker** | FlagEmbedding (optional, GPU-optional) |
| **Web Search** | Tavily API hoặc HTTP generic với whitelist domain |
| **Testing** | pytest, pytest-asyncio, respx |

---

## Cấu trúc dự án

```
MedChat_Agent/
├── backend/                        # FastAPI application
│   ├── main.py                     # Entry point, CORS, lifespan
│   └── api/
│       ├── routes.py               # /health /chat /chat/stream /ingest /sources/status
│       └── schemas.py              # Pydantic request/response models
│
├── core/                           # Business logic & ML pipeline
│   ├── chat_service.py             # Orchestrator chính (44KB)
│   ├── agent.py                    # Multi-label intent router (rule-based)
│   ├── router_classifier.py        # LLM-based intent classifier (optional)
│   ├── safety.py                   # Emergency detection, risk classification
│   ├── retrieval.py                # Qdrant hybrid search + reranking
│   ├── web_sources.py              # Whitelist web retrieval
│   ├── ingestion.py                # JSON chunk → Qdrant pipeline
│   ├── query_planner.py            # Multi-facet retrieval planning
│   ├── llm.py                      # LLM & embedding adapters (OpenAI/Gemini/DeepSeek)
│   ├── evidence_gate.py            # Coverage assessment & entity filtering
│   ├── evidence_checker.py         # LLM-based evidence validation
│   ├── answer_synthesizer.py       # Dynamic prompt building
│   ├── post_verifier.py            # Answer quality verification
│   ├── input_normalizer.py         # Vietnamese text normalization
│   ├── entity_resolver.py          # Drug/condition entity linking
│   ├── entity_merger.py            # Merge resolved entities
│   ├── citations.py                # Citation dedup & formatting
│   ├── config.py                   # Settings (Pydantic + .env)
│   ├── text.py                     # Mojibake repair, accent fold, normalize
│   └── cli.py                      # CLI ingestion tool
│
├── frontend/                       # React SPA
│   ├── src/
│   │   ├── App.jsx
│   │   ├── features/chat/          # ChatThread, MessageBubble, Composer, hooks
│   │   ├── components/             # UI primitives (Button, Card, Badge, Input...)
│   │   ├── pages/                  # Page-level components
│   │   └── context/               # Auth, Theme, Language, Toast
│   ├── package.json
│   └── vite.config.js
│
├── data/
│   ├── chunked/
│   │   ├── longchau_ingredients_chunked/   # 600+ hoạt chất dược
│   │   ├── thuoc_long_chau_chunked/        # Sản phẩm thuốc Long Châu
│   │   ├── tpcn_longchau_chunked/          # Thực phẩm chức năng
│   │   └── pharmacity_chunked/             # Bệnh lý & sức khỏe tổng quát
│   └── idf_weights.json                   # IDF weights cho sparse vector
│
├── evals/                          # RAGAS evaluation suite
├── tests/                          # Unit & integration tests
├── docs/superpowers/               # Architecture & design specs
├── requirements.txt
└── SETUP.md                        # Hướng dẫn cài đặt chi tiết
```

---

## Pipeline xử lý (16 bước)

```
POST /chat hoặc /chat/stream
  ↓
  1.  Validate request (Pydantic, max 16 000 ký tự)
  2.  Safety pre-check  →  nếu khẩn cấp: trả ngay emergency response
  3.  Input normalization (accent fold, mojibake repair)
  4.  Multi-intent router  →  rule-based + LLM optional
  5.  Entity resolution  (drug / condition linking, alias matching)
  6.  Entity merging
  7.  Query planning  (multi-facet, decompose intent → preferred fields)
  8.  Embed query  (local E5, 768-dim)
  9.  Qdrant hybrid retrieval  (dense + sparse RRF + trust-tier rerank)
  10. Evidence gate  (coverage: complete / usable_partial / weak_partial / insufficient / conflicting)
  11. Web retrieval  (whitelist-only, khi coverage < usable_partial)
  12. Evidence filter  (entity + field matching)
  13. Citation dedup & formatting
  14. LLM answer synthesis  (dynamic prompt theo coverage status)
  15. Post-verification  (hallucination check, high-risk advice check)
  16. Final response  →  JSON hoặc SSE stream
```

---

## Intent labels

| Intent | Mô tả | Risk |
|---|---|---|
| `emergency` | Triệu chứng khẩn cấp | URGENT |
| `interaction` | Tương tác thuốc | HIGH |
| `contraindication` | Chống chỉ định | HIGH |
| `pregnancy_lactation` | Mang thai, cho con bú | HIGH |
| `overdose` | Quá liều & xử trí | HIGH |
| `adverse_effect` | Tác dụng phụ | MEDIUM |
| `careful` | Thận trọng khi dùng | MEDIUM |
| `dosage` | Liều lượng & cách dùng | MEDIUM–HIGH |
| `pediatric_elderly` | Trẻ em, người cao tuổi | HIGH |
| `disease_context` | Bối cảnh bệnh lý | MEDIUM |
| `symptom_triage` | Phân loại triệu chứng | MEDIUM |
| `indication` | Công dụng, chỉ định | LOW |
| `drug_identity` | Tên thuốc, hoạt chất | LOW |
| `general_health` | Kiến thức y tế chung | LOW |
| `unsupported` | Ngoài phạm vi y tế | — |

---

## API Reference

### `POST /chat`

**Request**
```json
{
  "message": "Tôi đang uống warfarin, có dùng ibuprofen được không?",
  "conversation_id": null,
  "user_context": {
    "age": 67,
    "sex": "male",
    "pregnancy_status": "not_pregnant",
    "conditions": ["rung nhĩ"],
    "current_medications": ["warfarin"],
    "allergies": []
  },
  "preferences": {
    "language": "vi",
    "audience": "general",
    "include_technical_detail": false
  },
  "retrieval_options": {
    "allow_web": true,
    "qdrant_search": true,
    "max_sources": 8
  }
}
```

**Response**
```json
{
  "answer": "Warfarin và ibuprofen có tương tác nguy hiểm...",
  "safety_notice": "Thông tin này không thay thế tư vấn trực tiếp của nhân viên y tế.",
  "citations": [
    {
      "id": "S1",
      "title": "Warfarin - DailyMed",
      "url": "https://dailymed.nlm.nih.gov/...",
      "source": "dailymed.nlm.nih.gov",
      "trust_tier": "regulatory",
      "snippet": "..."
    }
  ],
  "intents": ["interaction", "contraindication"],
  "risk_level": "high",
  "evidence_status": "complete",
  "warnings": [],
  "confidence": "high",
  "requires_professional_advice": true
}
```

### `POST /chat/stream`

Cùng request schema với `/chat`. Response là Server-Sent Events:

```
data: {"token": "Warfarin"}
data: {"token": " và"}
...
data: {"done": true, "metadata": {...}}
```

### Các endpoint khác

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/ingest` | Nạp JSON chunks vào Qdrant |
| GET | `/sources/status` | Trạng thái collection Qdrant |

---

## Trust tiers

| Tier | Ví dụ nguồn | Mức ưu tiên |
|---|---|---|
| `regulatory` | FDA, DailyMed, EMA, Bộ Y tế VN | Cao nhất |
| `clinical_reference` | WHO, PubMed, medicines.org.uk | Cao |
| `local_curated` | Long Châu, Pharmacity corpus | Trung bình |
| `web_whitelisted` | Domain y tế trong whitelist | Thấp |

---

## Format dữ liệu ingestion

Mỗi file JSON trong `data/chunked/*/` là mảng chunk:

```json
[
  {
    "text": "Hoạt chất: Abacavir | Phần: Chỉ định | Nội dung: ...",
    "metadata": {
      "name": "Abacavir",
      "id": "abacavir",
      "url": "https://nhathuoclongchau.com.vn/thanh-phan/abacavir",
      "source": "Dược chất Long Châu",
      "field": "indication",
      "trust_tier": "local_curated",
      "source_family": "longchau_ingredients",
      "chunk_index": 0
    }
  }
]
```

**Các corpus được hỗ trợ:**

| Thư mục | Nội dung |
|---|---|
| `longchau_ingredients_chunked` | Hoạt chất & dược chất (600+) |
| `thuoc_long_chau_chunked` | Sản phẩm thuốc Long Châu |
| `tpcn_longchau_chunked` | Thực phẩm chức năng |
| `pharmacity_chunked` | Bệnh lý & chủ đề sức khỏe |

---

## Chạy tests

```bash
pytest tests/ -v
```

---

## Lưu ý vận hành

- Mô hình embedding chạy **local** sau lần tải đầu tiên, không cần API key ngoài.
- CORS mặc định chỉ cho phép `localhost:5173` — cần cập nhật khi deploy production.
- Ingestion tự động **skip chunk trùng lặp** (kiểm tra ID trước khi embed).
- Chunk bị lỗi encoding không thể sửa sẽ bị bỏ qua và ghi vào ingestion report.
- Cần cập nhật `WHITELIST_DOMAINS` trong `.env` để thêm/bớt domain web search.

---

> Xem hướng dẫn cài đặt chi tiết tại **[Setup_and_run.md](Setup_and_run.md)**.
