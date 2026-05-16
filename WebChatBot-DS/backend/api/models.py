from pydantic import BaseModel, Field
from typing import Optional, List


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    is_image: bool = False
    image: Optional[str] = None  # base64 data URI hoặc None


class MessageRecord(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: str  # ISO 8601
    sources: Optional[List[str]] = None
    image: Optional[str] = None  # base64 data URI hoặc None


class SessionSummary(BaseModel):
    id: str
    title: str
    preview: str
    date: str
    message_count: int
