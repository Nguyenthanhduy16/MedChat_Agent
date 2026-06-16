import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

from api.models import MessageRecord, SessionSummary


class SessionService:
    """Thread-safe in-memory session history store."""

    def __init__(self):
        self._store: Dict[str, List[MessageRecord]] = {}
        self._lock = threading.Lock()

    def add_user_message(self, session_id: str, content: str) -> MessageRecord:
        msg = MessageRecord(
            role="user",
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._store.setdefault(session_id, []).append(msg)
        return msg

    def add_assistant_message(
        self,
        session_id: str,
        content: str,
        sources: Optional[List[str]] = None,
        image: Optional[str] = None,
    ) -> MessageRecord:
        msg = MessageRecord(
            role="assistant",
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
            sources=sources,
            image=image,
        )
        with self._lock:
            self._store.setdefault(session_id, []).append(msg)
        return msg

    def session_exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._store

    def get_history(self, session_id: str) -> List[MessageRecord]:
        with self._lock:
            return list(self._store.get(session_id, []))

    def get_all_sessions(self) -> List[SessionSummary]:
        with self._lock:
            sessions = []
            for sid, messages in self._store.items():
                user_msgs = [m for m in messages if m.role == "user"]
                asst_msgs = [m for m in messages if m.role == "assistant"]

                title = (user_msgs[0].content[:50] + "...") if user_msgs else "Cuộc trò chuyện mới"
                preview = (
                    "Bot: " + asst_msgs[-1].content[:60] + "..."
                    if asst_msgs
                    else "Chưa có phản hồi"
                )
                date = messages[0].timestamp if messages else datetime.now(timezone.utc).isoformat()
                sessions.append(
                    SessionSummary(
                        id=sid,
                        title=title,
                        preview=preview,
                        date=date,
                        message_count=len(messages),
                    )
                )
            return sessions

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._store:
                del self._store[session_id]
                return True
            return False
