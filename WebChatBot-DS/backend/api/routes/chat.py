from fastapi import APIRouter, Request, HTTPException, status

from api.models import ChatRequest, ChatResponse

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Gửi tin nhắn và nhận câu trả lời từ chatbot",
)
async def post_chat(request: Request, body: ChatRequest):
    chat_service = request.app.state.chat_service
    svc = request.app.state.session_service

    svc.add_user_message(session_id=body.session_id, content=body.message)

    try:
        response: ChatResponse = await chat_service.process_message(body.message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi pipeline: {str(exc)}",
        ) from exc

    svc.add_assistant_message(
        session_id=body.session_id,
        content=response.answer,
        sources=response.sources,
        image=response.image,
    )

    return response
