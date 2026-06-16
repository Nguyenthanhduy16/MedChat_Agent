from typing import List

from fastapi import APIRouter, HTTPException, Request, status

from api.models import MessageRecord, SessionSummary

router = APIRouter()


@router.get(
    "/chat/history/{session_id}",
    response_model=List[MessageRecord],
    summary="Lấy lịch sử chat của một session",
)
async def get_chat_history(session_id: str, request: Request):
    svc = request.app.state.session_service
    if not svc.session_exists(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' không tồn tại.",
        )
    return svc.get_history(session_id)


@router.get(
    "/chat/sessions",
    response_model=List[SessionSummary],
    summary="Liệt kê tất cả sessions",
)
async def get_sessions(request: Request):
    return request.app.state.session_service.get_all_sessions()


@router.delete(
    "/chat/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa một session",
)
async def delete_session(session_id: str, request: Request):
    deleted = request.app.state.session_service.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' không tồn tại.",
        )
