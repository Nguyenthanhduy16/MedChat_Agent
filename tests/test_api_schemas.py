import pytest
from pydantic import ValidationError

from backend.api.schemas import ChatRequest, ChatResponse


def test_chat_request_accepts_optional_context() -> None:
    request = ChatRequest(
        message="Toi dang uong warfarin, co dung ibuprofen duoc khong?",
        user_context={
            "age": 67,
            "sex": "female",
            "pregnancy_status": "not_pregnant",
            "lactation": False,
            "conditions": ["rung nhi"],
            "current_medications": ["warfarin"],
            "allergies": [],
            "location": "VN",
        },
        retrieval_options={"allow_web": True, "max_sources": 8},
    )

    assert request.preferences.language == "vi"
    assert request.preferences.audience == "general"
    assert request.user_context.age == 67
    assert request.retrieval_options.max_sources == 8


def test_chat_request_rejects_empty_message() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="   ")


def test_chat_response_requires_evidence_status_and_warnings() -> None:
    response = ChatResponse(
        answer="Thong tin tham khao.",
        safety_notice="Khong thay the tu van y te chuyen nghiep.",
        citations=[],
        intents=["interaction"],
        risk_level="high",
        evidence_status="partial",
        warnings=["Can xac minh them danh sach thuoc dang dung."],
        confidence="medium",
        requires_professional_advice=True,
    )

    assert response.evidence_status == "partial"
    assert response.warnings == ["Can xac minh them danh sach thuoc dang dung."]
