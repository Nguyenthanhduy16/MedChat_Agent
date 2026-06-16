import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Thêm backend/ vào sys.path để import tuyệt đối "from query.xxx" hoạt động
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.chat_service import ChatService
from services.session_service import SessionService
from api.routes.chat import router as chat_router
from api.routes.history import router as history_router
from api.routes.analytics import router as analytics_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Khởi động: đang khởi tạo ChatService và RouterPipeline...")
    app.state.session_service = SessionService()
    app.state.chat_service = ChatService()
    logger.info("Khởi động hoàn tất.")
    yield
    logger.info("Tắt server.")


app = FastAPI(
    title="MedAgent API",
    description="Backend chatbot tư vấn dược — RAG pipeline + SQLite store pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(history_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
