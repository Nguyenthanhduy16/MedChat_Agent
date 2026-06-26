# Hướng dẫn cài đặt & chạy MedChat Agent

---

## Mục lục

1. [Yêu cầu hệ thống](#1-yêu-cầu-hệ-thống)
2. [Clone dự án](#2-clone-dự-án)
3. [Cài đặt Qdrant](#3-cài-đặt-qdrant)
4. [Cấu hình biến môi trường](#4-cấu-hình-biến-môi-trường)
5. [Cài đặt backend (Python)](#5-cài-đặt-backend-python)
6. [Nạp dữ liệu vào Qdrant](#6-nạp-dữ-liệu-vào-qdrant)
7. [Cài đặt frontend (Node.js)](#7-cài-đặt-frontend-nodejs)
8. [Chạy hệ thống](#8-chạy-hệ-thống)
9. [Kiểm tra hệ thống](#9-kiểm-tra-hệ-thống)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Yêu cầu hệ thống

| Thành phần | Phiên bản tối thiểu | Ghi chú |
|---|---|---|
| **Python** | 3.11+ | Khuyên dùng 3.11 hoặc 3.12 |
| **Node.js** | 18+ | Kèm npm 9+ |
| **Docker** | 20+ | Để chạy Qdrant (hoặc dùng Qdrant Cloud) |
| **RAM** | 4 GB+ | 8 GB+ nếu dùng reranker local |
| **Disk** | 3 GB+ | Cho model embedding (~500 MB) + corpus data |

**API Keys cần có:**

| Key | Bắt buộc | Dùng cho |
|---|---|---|
| `OPENAI_API_KEY` | Có (hoặc DeepSeek) | LLM chính |
| `GEMINI_API_KEY` | Không (fallback) | LLM dự phòng |
| `DEEPSEEK_API_KEY` | Không (thay thế OpenAI) | LLM alternative |
| `WEB_SEARCH_API_KEY` | Không | Web retrieval (Tavily) |

---

## 2. Clone dự án

```bash
git clone <repo-url> MedChat_Agent
cd MedChat_Agent
```

---

## 3. Cài đặt Qdrant

### Dùng Docker (khuyến nghị)

```bash
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

Kiểm tra Qdrant đã chạy:

```bash
curl http://localhost:6333/healthz
# Kết quả: {"title":"qdrant - vector search engine","version":"..."}
```

### Dùng Qdrant Cloud

Tạo cluster tại [cloud.qdrant.io](https://cloud.qdrant.io), lấy URL và API key, điền vào `.env` ở bước 4.

---

## 4. Cấu hình biến môi trường

Tạo file `.env` ở thư mục gốc (`MedChat_Agent/.env`):

```dotenv
# ============================================================
# LLM Providers — chọn ít nhất một provider
# ============================================================

# OpenAI (primary)
OPENAI_API_KEY=sk-...

# DeepSeek (thay thế OpenAI, dùng OpenAI-compatible API)
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Google Gemini (fallback khi provider chính lỗi)
GEMINI_API_KEY=AIza...

# ============================================================
# Model Selection
# ============================================================

# Model LLM chính — dùng tên model của provider bạn chọn
# Ví dụ OpenAI:   gpt-4o-mini
# Ví dụ DeepSeek: deepseek-v4-0414
CHAT_MODEL=gpt-4o-mini

# Model Gemini fallback
GEMINI_MODEL=gemini-2.5-flash

# ============================================================
# Embedding — chạy local, không cần API key
# ============================================================

EMBEDDING_MODEL=intfloat/multilingual-e5-base

# ============================================================
# Qdrant Vector Database
# ============================================================

# Local Docker
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# Qdrant Cloud (thay thế hai dòng trên)
# QDRANT_URL=https://<cluster-id>.eu-central.aws.cloud.qdrant.io:6333
# QDRANT_API_KEY=<your-qdrant-api-key>

QDRANT_COLLECTION=pharmacy_chunks

# ============================================================
# Web Search (tùy chọn)
# ============================================================

WEB_SEARCH_PROVIDER=tavily
WEB_SEARCH_ENDPOINT=https://api.tavily.com/search
WEB_SEARCH_API_KEY=tvly-...
WEB_SEARCH_TIMEOUT_SECONDS=8.0

# ============================================================
# Router & Evidence (có thể giữ mặc định)
# ============================================================

LLM_ROUTER_ENABLED=true
LLM_ROUTER_CONFIDENCE_THRESHOLD=0.6
LLM_ROUTER_TIMEOUT_SECONDS=8.0

LLM_EVIDENCE_CHECKER_ENABLED=false
LLM_EVIDENCE_CHECKER_TIMEOUT_SECONDS=12.0

# ============================================================
# Retrieval
# ============================================================

LOCAL_TOP_K_PER_INTENT=6
FINAL_CITATIONS_MIN=3
FINAL_CITATIONS_MAX=8
MAX_EVIDENCE_CHUNKS_FOR_LLM=12

# ============================================================
# Reranker (tùy chọn, cần GPU để đạt tốc độ tốt)
# ============================================================

RERANKER_MODEL=
RERANKER_USE_FP16=true
RERANKER_TIMEOUT_SECONDS=10.0

# ============================================================
# Timeouts
# ============================================================

CHAT_TIMEOUT_SECONDS=60.0
LLM_TIMEOUT_SECONDS=30.0
EMBEDDING_TIMEOUT_SECONDS=60.0
QDRANT_QUERY_TIMEOUT_SECONDS=5.0
```

---

## 5. Cài đặt backend (Python)

### Tạo virtual environment (khuyến nghị)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### Cài dependencies

```bash
pip install -r requirements.txt
```

> **Lưu ý:** `sentence-transformers` sẽ tự tải model `intfloat/multilingual-e5-large` (~500 MB) vào cache Hugging Face (`~/.cache/huggingface/`) trong lần chạy đầu tiên. Cần có internet.

### (Tùy chọn) Tải model embedding trước

Nếu muốn tải model trước khi khởi động server:

```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-base'); print('Done')"
```

---

## 6. Nạp dữ liệu vào Qdrant

Bước này cần Qdrant đang chạy (bước 3) và `.env` đã cấu hình (bước 4).

### Cách 1: Qua CLI (offline, không cần server)

```bash
python -m core.cli --path data/chunked
```

Output mẫu:
```
[Ingestion] Scanning data/chunked...
[Ingestion] Found 4 corpus directories
[Ingestion] longchau_ingredients_chunked: 3 247 chunks → indexed 3 241, skipped 6
[Ingestion] thuoc_long_chau_chunked: 1 890 chunks → indexed 1 890, skipped 0
[Ingestion] tpcn_longchau_chunked: 412 chunks → indexed 412, skipped 0
[Ingestion] pharmacity_chunked: 723 chunks → indexed 723, skipped 0
[Ingestion] Tổng: 6 272 chunks indexed
```

### Cách 2: Qua API (sau khi server đã chạy)

```bash
curl -X POST http://localhost:8000/ingest
```

### Kiểm tra sau ingestion

```bash
curl http://localhost:6333/collections/pharmacy_chunks
```

Kết quả nên có `"vectors_count"` > 0.

---

## 7. Cài đặt frontend (Node.js)

```bash
cd frontend
npm install
```

### (Tùy chọn) Cấu hình URL backend

Mặc định frontend kết nối `http://localhost:8000`. Để thay đổi, tạo file `frontend/.env.local`:

```dotenv
VITE_API_URL=http://localhost:8000
```

---

## 8. Chạy hệ thống

### Terminal 1 — Backend

```bash
# Từ thư mục gốc MedChat_Agent/
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Chờ đến khi thấy log:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

Chờ đến khi thấy log:
```
  VITE v8.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
```

### Truy cập

| Địa chỉ | Mô tả |
|---|---|
| http://localhost:5173 | Giao diện web |
| http://localhost:8000/docs | Swagger UI (API docs) |
| http://localhost:8000/redoc | ReDoc (API docs) |
| http://localhost:8000/health | Health check |

---

## 9. Kiểm tra hệ thống

### Health check

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### Trạng thái vector database

```bash
curl http://localhost:8000/sources/status
```

### Gửi câu hỏi thử

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Paracetamol liều dùng cho người lớn là bao nhiêu?",
    "retrieval_options": {"allow_web": false}
  }'
```

### Chạy test suite

```bash
pytest tests/ -v
```

---

## 10. Troubleshooting

### Lỗi kết nối Qdrant

```
qdrant_client.http.exceptions.UnexpectedResponse: Status 401
```

**Nguyên nhân:** QDRANT_API_KEY sai hoặc để trống khi dùng Qdrant Cloud.
**Cách sửa:** Kiểm tra lại `QDRANT_API_KEY` trong `.env`.

---

### Lỗi OpenAI API key

```
openai.AuthenticationError: Incorrect API key
```

**Cách sửa:** Kiểm tra `OPENAI_API_KEY` trong `.env`. Key phải bắt đầu bằng `sk-`.

---

### Model embedding tải chậm / lỗi mạng

```
OSError: We couldn't connect to 'https://huggingface.co'
```

**Nguyên nhân:** Không có internet trong lần chạy đầu.
**Cách sửa:** Tải trước khi có mạng (xem bước 5), hoặc đặt biến môi trường:

```bash
# Windows
set HF_ENDPOINT=https://hf-mirror.com

# Linux / macOS
export HF_ENDPOINT=https://hf-mirror.com
```

---

### Port đã được sử dụng

```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)
```

**Cách sửa:** Dùng port khác:

```bash
uvicorn backend.main:app --port 8001 --reload
```

Sau đó cập nhật `VITE_API_URL=http://localhost:8001` trong `frontend/.env.local`.

---

### Frontend không kết nối được backend

**Kiểm tra:**
1. Backend đang chạy trên port 8000 (`curl http://localhost:8000/health`).
2. `VITE_API_URL` trong `frontend/.env.local` đúng.
3. Không có firewall/proxy chặn port 8000.

---

### Ingestion chậm hoặc bị treo

**Nguyên nhân:** Embed toàn bộ corpus lần đầu mất thời gian (~5–15 phút tuỳ phần cứng).

**Theo dõi tiến độ:**
```bash
# Xem số vector đã index
curl http://localhost:6333/collections/pharmacy_chunks | python -m json.tool
```

---

### Lỗi `CORS` khi gọi API từ browser

**Cách sửa:** Thêm origin của bạn vào `ALLOWED_ORIGINS` trong `backend/main.py`, hoặc dùng đúng port 5173 cho frontend.

---

## Ghi chú nhanh

```bash
# Khởi động lại toàn bộ (sau khi tắt máy)
docker start qdrant                                      # khởi động lại Qdrant
uvicorn backend.main:app --port 8000 --reload &          # backend
cd frontend && npm run dev                               # frontend

# Xóa collection và ingest lại từ đầu
curl -X DELETE http://localhost:6333/collections/pharmacy_chunks
python -m core.cli --path data/chunked
```
