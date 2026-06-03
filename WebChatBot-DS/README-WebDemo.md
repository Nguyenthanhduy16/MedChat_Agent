# MedAgent — Chatbot Tư Vấn Dược

Ứng dụng chatbot hỗ trợ tư vấn dược phẩm và phân tích kho thuốc, sử dụng RAG pipeline kết hợp SQLite analytics.

## Tính năng

- **Tư vấn y tế** — Trả lời câu hỏi về thuốc, triệu chứng, liều lượng qua RAG (Qdrant vector search + GPT-4o-mini)
- **Phân tích kho thuốc** — Truy vấn dữ liệu kho hàng, giá cả, thống kê bằng SQL tự động
- **Vẽ biểu đồ** — Sinh biểu đồ trực quan (bar, line, pie...) từ dữ liệu SQLite
- **Lịch sử chat** — Lưu và xem lại các cuộc trò chuyện theo session

## Tech Stack

| Layer | Công nghệ |
|-------|-----------|
| Frontend | React 19, Vite, TailwindCSS 4, Axios |
| Backend | FastAPI, Python 3.11+, Uvicorn |
| LLM | OpenAI GPT-4o-mini |
| Embedding | Google text-embedding-004 |
| Vector DB | Qdrant Cloud |
| Relational DB | SQLite + SQLAlchemy |
| Web Search | DuckDuckGo + Playwright (fallback) |
| Chart | Matplotlib, Pillow |

## Cấu trúc dự án

```
WebChatBot-DS/
├── frontend/                          React app (port 5173)
│   └── src/
│       ├── features/chat/
│       │   ├── hooks/                 useChat.js, useConversations.js
│       │   ├── services/chatApi.js    Định nghĩa API calls
│       │   └── components/            ChatThread, MessageBubble, Composer
│       ├── pages/                     LandingPage, ChatPage
│       └── services/api.js            Axios instance (timeout 60s)
└── backend/                           FastAPI app (port 8000)
    ├── main.py                        Entry point, CORS, lifespan
    ├── .env                           API keys (không commit)
    ├── requirements.txt
    ├── query/                         Pipeline (không sửa)
    │   ├── router_pipeline.py         Orchestrator chính
    │   ├── medical_query_pipeline.py  RAG pipeline + retry
    │   ├── store/store_pipeline.py    SQLite + chart pipeline
    │   ├── router/router.py           LLM router
    │   └── core/                      LLM factory, embedding, models
    ├── sqlite-db/
    │   └── database/drug-warehouse.db (~21MB)
    ├── api/
    │   ├── models.py                  Pydantic request/response models
    │   └── routes/                    chat.py, history.py
    └── services/
        ├── chat_service.py            Wrap RouterPipeline + base64 chart
        └── session_service.py         In-memory session store
```

## Cài đặt

### Yêu cầu

- Python 3.11+
- Node.js 18+
- Tài khoản: OpenAI API, Google AI Studio, Qdrant Cloud

### 1. Clone và cấu hình

```bash
git clone <repo-url>
cd WebChatBot-DS
```

Tạo file `backend/.env`:

```dotenv
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
QDRANT_URL=https://xxx.qdrant.io
QDRANT_API_KEY=...
```

### 2. Cài backend

```bash
cd backend
pip install -r requirements.txt
python -m playwright install chromium
```

### 3. Cài frontend

```bash
cd frontend
npm install
```

## Chạy

**Terminal 1 — Backend:**

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Chờ log: `RouterPipeline đã sẵn sàng.` (khoảng 10-15 giây)

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

Mở trình duyệt tại [http://localhost:5173](http://localhost:5173)

## API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/health` | Health check |
| POST | `/api/chat` | Gửi tin nhắn, nhận câu trả lời |
| GET | `/api/chat/history/{sessionId}` | Lịch sử chat của session |
| GET | `/api/chat/sessions` | Danh sách tất cả sessions |
| DELETE | `/api/chat/sessions/{sessionId}` | Xóa session |

**Request `POST /api/chat`:**
```json
{ "session_id": "uuid-string", "message": "Paracetamol có tác dụng gì?" }
```

**Response:**
```json
{
  "answer": "Paracetamol là thuốc giảm đau, hạ sốt...",
  "sources": ["Nguồn 1", "Nguồn 2"],
  "is_image": false,
  "image": null
}
```

Khi có biểu đồ, `is_image: true` và `image` là base64 data URI (`data:image/png;base64,...`).

## Kiến trúc Pipeline

```
User message
    │
    ▼
Router (GPT-4o-mini)
    │
    ├── medical_knowledge ──► Qdrant RAG ──► GPT answer ──► Response
    │                              │ (fail)
    │                              └──► Web search fallback
    │
    └── store_database ──► SQL generation ──► SQLite ──► Text / Chart
```

Toàn bộ pipeline là **synchronous** (LangChain, Playwright) — FastAPI gọi qua `asyncio.run_in_executor` để không block event loop.

## Lưu ý

- Session history lưu **in-memory** — mất khi restart server
- Ảnh biểu đồ truyền qua JSON dưới dạng base64 PNG
- CORS chỉ cho phép `localhost:5173`
- Để đổi backend URL: tạo `frontend/.env.local` với `VITE_API_URL=http://...`
