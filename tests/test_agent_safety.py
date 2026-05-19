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


def test_retrieval_plan_does_not_field_filter_drug_identity_questions() -> None:
    decision = route_question(ChatRequest(message="Paracetamol la thuoc gi?"))
    plan = build_retrieval_plan(decision)

    assert decision.intents == ["drug_identity"]
    assert "field" not in plan.metadata_filters
    assert plan.entities["drugs"] == ["paracetamol"]


def test_retrieval_plan_does_not_field_filter_general_health_questions() -> None:
    decision = route_question(ChatRequest(message="Toi bi dau dau nen lam gi?"))
    plan = build_retrieval_plan(decision)

    assert decision.intents == ["general_health"]
    assert "field" not in plan.metadata_filters


def test_router_marks_non_medical_question_as_unsupported() -> None:
    decision = route_question(ChatRequest(message="Cach dat A+ Giai tich"))

    assert decision.intents == ["unsupported"]
    assert decision.risk_level == RiskLevel.LOW


def test_router_extracts_named_product_from_drug_name_question() -> None:
    decision = route_question(ChatRequest(message="Thuoc Zoacnel 5mg Davi"))
    plan = build_retrieval_plan(decision)

    assert decision.intents == ["drug_identity"]
    assert decision.entities["drugs"] == ["Zoacnel 5mg Davi"]
    assert "Zoacnel 5mg Davi" in plan.queries[0]
    assert "general_health" not in plan.queries[0]


def test_router_extracts_named_condition_from_cancer_question() -> None:
    decision = route_question(ChatRequest(message="Ung thư vú"))
    plan = build_retrieval_plan(decision)

    assert decision.intents == ["disease_context"]
    assert decision.entities["conditions"] == ["Ung thư vú"]
    assert "Ung thư vú" in plan.queries[0]
    assert "unsupported" not in plan.queries[0]
