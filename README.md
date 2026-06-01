# MedChat Agent

Chatbot tư vấn dược phẩm AI, kết hợp RAG pipeline từ kho kiến thức y tế với phân tích kho hàng qua SQL tự động, có giao diện web đầy đủ.

AI薬事相談チャットボット。医療知識ベースのRAGパイプラインと、SQL自動生成による在庫分析機能を組み合わせた、フルスタックWebアプリケーションです。

---

## Tính năng / 機能

- **Tư vấn y tế** — Trả lời câu hỏi về thuốc, liều lượng, tương tác, chống chỉ định bằng tiếng Việt, có trích dẫn nguồn  
  **医療相談** — 薬・用量・相互作用・禁忌に関するベトナム語での質問に、出典付きで回答

- **Safety guardrails** — Phát hiện tình huống khẩn cấp, phân loại rủi ro, từ chối câu hỏi ngoài phạm vi y tế  
  **安全ガード機能** — 緊急症状の検出、リスクレベル分類、医療範囲外の質問の拒否

- **Hybrid retrieval** — Kết hợp dense vector search (Qdrant) và sparse keyword matching, reranking theo trust tier  
  **ハイブリッド検索** — 密なベクトル検索（Qdrant）とスパースキーワードマッチングを組み合わせ、信頼度階層によるリランキング

- **Web retrieval có kiểm soát** — Tìm kiếm bổ sung từ danh sách domain uy tín (FDA, WHO, PubMed, MOH VN...)  
  **制御付きWeb検索** — FDA・WHO・PubMed・ベトナム保健省など信頼済みドメインからの補足情報取得

- **Phân tích kho hàng** — Truy vấn dữ liệu tồn kho, giá cả, thống kê qua SQL tự動 sinh từ LLM  
  **在庫分析** — LLMが自動生成するSQLで在庫・価格・統計データを照会

- **Vẽ biểu đồ** — Sinh biểu đồ bar, line, pie, area từ kết quả truy vấn SQLite  
  **グラフ描画** — SQLiteクエリ結果からbar・line・pie・areaチャートを自動生成

- **Lịch sử chat** — Lưu và xem lại các cuộc trò chuyện theo session  
  **チャット履歴** — セッション単位での会話保存と閲覧

- **Multi-intent routing** — Phân loại câu hỏi thành nhiều intent và xây dựng retrieval plan tương ứng  
  **マルチインテントルーティング** — 質問を複数インテントに分類し、対応する検索プランを構築

---

## Tech Stack

| Layer / レイヤー | Công nghệ / 技術 |
|---|---|
| Frontend / フロントエンド | React 19, Vite, TailwindCSS 4, Axios |
| Backend API | FastAPI, Python 3.11+, Uvicorn |
| LLM | OpenAI GPT-4o-mini (primary), Google Gemini 2.5 Flash (fallback) |
| Embedding / 埋め込みモデル | `intfloat/multilingual-e5-base`（ローカル・オフライン） |
| Vector DB / ベクトルDB | Qdrant（ローカルまたはCloud） |
| Relational DB / リレーショナルDB | SQLite + SQLAlchemy |
| Web Search / Web検索 | Whitelist HTTP/Tavily（医療相談）、DuckDuckGo + Playwright（在庫分析） |
| Chart / グラフ | Matplotlib, Pillow |
| Testing / テスト | pytest, pytest-asyncio, respx |

---

## Cấu trúc dự án / プロジェクト構成

```
MedChat_Agent/
├── backend/                        FastAPI app (nhánh core / コアバックエンド)
│   ├── main.py                     Entry point
│   └── api/
│       ├── routes.py               /chat, /ingest, /sources/status, /health
│       └── schemas.py              Pydantic request/response models
├── core/                           Business logic / ビジネスロジック
│   ├── agent.py                    Multi-label intent router + retrieval planner
│   ├── chat_service.py             Orchestrator (safety → route → retrieve → generate)
│   ├── citations.py                Citation formatting và dedup / 引用フォーマット・重複排除
│   ├── cli.py                      CLI ingestion tool
│   ├── config.py                   Settings từ .env / 設定管理
│   ├── evidence.py                 Evidence sufficiency gate / 証拠十分性チェック
│   ├── ingestion.py                JSON chunk pipeline → Qdrant
│   ├── llm.py                      Provider-agnostic LLM & embedding adapters
│   ├── models.py                   Domain models (EvidenceItem, RouterDecision...)
│   ├── retrieval.py                Qdrant hybrid retrieval + reranking
│   ├── safety.py                   Safety pre-check, urgent response / 安全チェック
│   ├── text.py                     Encoding repair, accent fold, normalize / テキスト正規化
│   └── web_sources.py              Whitelist web retrieval / ホワイトリストWeb検索
├── WebChatBot-DS/                  Web demo (fullstack / フルスタックデモ)
│   ├── frontend/                   React app (port 5173)
│   │   └── src/
│   │       ├── features/chat/      ChatThread, MessageBubble, Composer, hooks
│   │       ├── pages/              LandingPage, ChatPage, AuthPage
│   │       └── context/            Auth, Theme, Language, Toast
│   └── backend/                    FastAPI app (port 8000)
│       ├── main.py                 Entry point, CORS, lifespan
│       ├── query/
│       │   ├── router_pipeline.py  Orchestrator: medical RAG or store SQL
│       │   ├── medical_query_pipeline.py  RAG + eval + retry + web fallback
│       │   ├── store/store_pipeline.py    SQL generation + chart rendering
│       │   ├── router/router.py    LLM router (medical vs store)
│       │   ├── medical/            MedicalRAG, MedicalSearch, MedicalPipeline
│       │   └── core/               LLM factory, embedding, data structures
│       ├── api/                    Pydantic models, routes (chat, history, analytics)
│       └── services/               ChatService, SessionService
├── tests/                          Unit và integration tests / ユニット・統合テスト
├── docs/superpowers/               Spec và implementation plans / 設計仕様書
├── requirements.txt
└── pytest.ini
```

---

## Kiến trúc tổng thể / システムアーキテクチャ

### Luồng tư vấn y tế / 医療相談フロー

```
POST /chat
  → Validate request           リクエスト検証
  → Safety pre-check           安全チェック（緊急症状 → 即時応答）
  → Multi-label intent router  マルチインテント分類
  → Build retrieval plan       検索プラン構築
  → Embed query (local E5)     クエリ埋め込み（ローカルモデル）
  → Qdrant hybrid retrieval    ハイブリッド検索 + リランキング
  → Evidence sufficiency gate  証拠十分性チェック
  → Web retrieval (whitelist)  Web補足検索（ホワイトリスト）
  → LLM generate answer        LLM回答生成
  → Citation completeness      引用完全性チェック
  → Structured JSON response   構造化JSONレスポンス
```

### Luồng phân tích kho hàng / 在庫分析フロー

```
POST /api/chat (store_database route)
  → LLM Router phân loại câu hỏi về kho  在庫関連質問の検出
  → GPT sinh QueryPlan (SQL + chart config)  SQLと図設定の自動生成
  → SQLAlchemy execute trên drug-warehouse.db  SQLite実行
  → need_chart=true: Matplotlib render → base64 PNG  グラフ描画
  → need_chart=false: GPT tổng hợp text answer  テキスト回答生成
  → JSON response (answer + image)
```

### Intent labels / インテント一覧

| Intent | Mô tả / 説明 | Risk / リスク |
|---|---|---|
| `drug_identity` | Tên thuốc, hoạt chất / 薬名・有効成分 | LOW |
| `indication` | Công dụng, chỉ định / 適応症・用途 | LOW |
| `dosage` | Liều lượng, cách dùng / 用量・用法 | MEDIUM–HIGH |
| `interaction` | Tương tác thuốc / 薬物相互作用 | HIGH |
| `contraindication` | Chống chỉ định / 禁忌 | HIGH |
| `pregnancy_lactation` | Mang thai, cho con bú / 妊娠・授乳 | HIGH |
| `pediatric_elderly` | Trẻ em, người cao tuổi / 小児・高齢者 | HIGH |
| `disease_context` | Bối cảnh bệnh lý / 病態背景 | MEDIUM |
| `symptom_triage` | Phân loại triệu chứng / 症状トリアージ | MEDIUM |
| `general_health` | Kiến thức y tế chung / 一般医療知識 | LOW |
| `emergency` | Triệu chứng khẩn cấp / 緊急症状 | URGENT |
| `unsupported` | Ngoài phạm vi y tế / 医療範囲外 | — |

---

## Cài đặt / セットアップ

### Yêu cầu / 前提条件

- Python 3.11+
- Node.js 18+
- Qdrant đang chạy / Qdrant起動済み (`docker run -p 6333:6333 qdrant/qdrant`)
- API key: OpenAI và/hoặc Google AI Studio / OpenAIまたはGoogle AI StudioのAPIキー

### 1. Clone và cấu hình / クローンと設定

```bash
git clone <repo-url>
cd MedChat_Agent
```

Tạo file `.env` ở thư mục gốc / ルートディレクトリに `.env` を作成:

```dotenv
# LLM
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...          # tùy chọn / オプション（フォールバック用）

# Embedding (local, không cần key / ローカル実行、APIキー不要)
EMBEDDING_MODEL=intfloat/multilingual-e5-base

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=                 # để trống nếu dùng local / ローカル使用時は空白
QDRANT_COLLECTION=pharmacy_chunks

# Web search (tùy chọn / オプション)
WEB_SEARCH_PROVIDER=tavily      # hoặc generic / またはgeneric
WEB_SEARCH_ENDPOINT=https://api.tavily.com/search
WEB_SEARCH_API_KEY=tvly-...
```

### 2. Cài backend core / コアバックエンドのインストール

```bash
pip install -r requirements.txt
python -m playwright install chromium   # chỉ cần cho WebDemo / WebDemoのみ必要
```

### 3. Nạp dữ liệu vào Qdrant / データのQdrantへの投入

```bash
# Qua CLI / CLIから
python -m core.cli --path data/chunks

# Hoặc qua API / またはAPIから（サーバー起動後）
curl -X POST http://localhost:8000/ingest
```

### 4. Cài frontend (WebDemo) / フロントエンドのインストール

```bash
cd WebChatBot-DS/frontend
npm install
```

---

## Chạy / 起動方法

### Core backend (port 8000)

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### WebDemo backend (port 8000)

```bash
cd WebChatBot-DS/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Chờ log / 起動完了ログ: `RouterPipeline đã sẵn sàng.`

### Frontend (port 5173)

```bash
cd WebChatBot-DS/frontend
npm run dev
```

Mở trình duyệt / ブラウザで開く: [http://localhost:5173](http://localhost:5173)

---

## API Endpoints

### Core backend

| Method | Endpoint | Mô tả / 説明 |
|---|---|---|
| GET | `/health` | Health check / ヘルスチェック |
| POST | `/chat` | Tư vấn y tế / 医療相談（回答＋引用＋リスク） |
| POST | `/ingest` | Nạp JSON chunks vào Qdrant / データ投入 |
| GET | `/sources/status` | Trạng thái collection / コレクション状態確認 |

**Request `POST /chat`:**
```json
{
  "message": "Tôi đang uống warfarin, có dùng ibuprofen được không?",
  "user_context": {
    "age": 67,
    "pregnancy_status": "not_pregnant",
    "conditions": ["rung nhĩ"]
  },
  "retrieval_options": {
    "allow_web": true,
    "qdrant_search": true
  }
}
```

**Response `POST /chat`:**
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
  "evidence_status": "sufficient",
  "warnings": [],
  "confidence": "medium",
  "requires_professional_advice": true
}
```

### WebDemo backend

| Method | Endpoint | Mô tả / 説明 |
|---|---|---|
| GET | `/health` | Health check / ヘルスチェック |
| POST | `/api/chat` | Gửi tin nhắn (y tế hoặc kho hàng) / メッセージ送信（医療または在庫） |
| GET | `/api/chat/history/{sessionId}` | Lịch sử chat / チャット履歴取得 |
| GET | `/api/chat/sessions` | Danh sách sessions / セッション一覧 |
| DELETE | `/api/chat/sessions/{sessionId}` | Xóa session / セッション削除 |

**Request `POST /api/chat`:**
```json
{ "session_id": "uuid-string", "message": "Vẽ biểu đồ top 5 thuốc bán chạy nhất" }
```

**Response khi có biểu đồ / グラフあり時のレスポンス:**
```json
{
  "answer": "**Top 5 thuốc bán chạy nhất**\n\n| Thuốc | Doanh thu |...",
  "sources": ["Database"],
  "is_image": true,
  "image": "data:image/png;base64,..."
}
```

---

## Format dữ liệu chunk (Ingestion) / チャンクデータ形式

`data/chunks/` 以下の各JSONファイルは、チャンクオブジェクトの配列を含みます:

```json
[
  {
    "text": "Hoạt chất: Abacavir | Phần: Chỉ định | Nội dung: ...",
    "metadata": {
      "name": "Abacavir",
      "id": "abacavir",
      "url": "https://nhathuoclongchau.com.vn/thanh-phan/abacavir",
      "category": "Dược chất LC",
      "type": "Dược chất",
      "source": "Dược chất Long Châu",
      "field": "indication",
      "chunk_index": 0
    }
  }
]
```

Các thư mục corpus được hỗ trợ / サポートされているコーパスディレクトリ:

| Thư mục / ディレクトリ | Nội dung / 内容 |
|---|---|
| `longchau_ingredients_chunked` | Hoạt chất và dược chất / 有効成分・薬物成分 |
| `thuoc_long_chau_chunked` | Sản phẩm thuốc Long Châu / Long Châu薬品製品 |
| `tpcn_longchau_chunked` | Thực phẩm chức năng / 機能性食品 |
| `pharmacity_chunked` | Bệnh lý và chủ đề sức khỏe / 疾患・健康トピック |

---

## Trust tiers / 信頼度階層

| Tier | Nguồn / 信頼元 | Ví dụ / 例 |
|---|---|---|
| `regulatory` | Cơ quan quản lý dược / 規制当局 | FDA, DailyMed, EMA, MOH VN |
| `clinical_reference` | Tài liệu lâm sàng / 臨床参考文献 | WHO, PubMed, medicines.org.uk |
| `local_curated` | Corpus JSON cục bộ / ローカルコーパス | Long Châu, Pharmacity |
| `web_whitelisted` | Web nguồn uy tín khác / その他承認済みWeb | ホワイトリスト内ドメイン |

---

## Chạy tests / テスト実行

```bash
pytest tests/ -v
```

---

## Lưu ý / 注意事項

- Session history trong WebDemo lưu **in-memory** — mất khi restart server  
  WebDemoのセッション履歴は**メモリ上**に保存されます — サーバー再起動時に消去されます

- Mô hình embedding chạy **local** (offline sau lần tải đầu tiên), không cần gọi API ngoài  
  埋め込みモデルは**ローカル実行**（初回ダウンロード後はオフライン対応）、外部API呼び出し不要

- CORS trong WebDemo chỉ cho phép `localhost:5173`, cần cập nhật khi deploy  
  WebDemoのCORSは`localhost:5173`のみ許可 — デプロイ時は設定変更が必要

- Để đổi backend URL cho frontend: tạo `WebChatBot-DS/frontend/.env.local` với `VITE_API_URL=http://...`  
  フロントエンドのバックエンドURL変更: `WebChatBot-DS/frontend/.env.local` に `VITE_API_URL=http://...` を追加

- Ingestion tự động skip chunk trùng lặp (kiểm tra ID trước khi embed)  
  データ投入時、重複チャンクは自動スキップ（埋め込み前にID照合）

- Chunk bị lỗi encoding không thể sửa sẽ bị bỏ qua và ghi vào ingestion report  
  修復不可能なエンコーディングエラーのチャンクはスキップし、投入レポートに記録
