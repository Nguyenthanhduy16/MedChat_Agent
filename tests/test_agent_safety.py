from backend.api.schemas import ChatRequest
from core.agent import build_retrieval_plan, route_question
from core.models import RiskLevel
from core.safety import safety_precheck


def test_router_returns_multi_label_for_interaction_question() -> None:
    decision = route_question(
        ChatRequest(message="Toi dang uong warfarin, co dung ibuprofen duoc khong?")
    )

    assert "interaction" in decision.intents
    assert "contraindication" in decision.intents
    assert decision.risk_level == RiskLevel.HIGH
    assert "warfarin" in decision.entities["drugs"]
    assert "ibuprofen" in decision.entities["drugs"]


def test_router_marks_pregnancy_as_high_risk() -> None:
    decision = route_question(ChatRequest(message="Phu nu mang thai dung isotretinoin duoc khong?"))

    assert "pregnancy_lactation" in decision.intents
    assert decision.risk_level == RiskLevel.HIGH


def test_safety_precheck_marks_breathing_overdose_as_urgent() -> None:
    result = safety_precheck("Toi uong qua lieu thuoc X va dang kho tho")

    assert result.risk_level == RiskLevel.URGENT
    assert result.should_short_circuit is True


def test_retrieval_plan_includes_filters_and_entities() -> None:
    decision = route_question(ChatRequest(message="Warfarin va ibuprofen co tuong tac khong?"))
    plan = build_retrieval_plan(decision)

    assert "interaction" in plan.metadata_filters["field"]
    assert plan.entities["drugs"] == ["warfarin", "ibuprofen"]
