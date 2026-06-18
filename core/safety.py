from dataclasses import dataclass

from core.models import RiskLevel
from core.text import accent_fold


URGENT_TERMS = (
    "kho tho",
    "dau nguc",
    "co giat",
    "mat y thuc",
    "phan ve",
    "qua lieu",
    "ngo doc",
    "tu tu",
)


@dataclass(frozen=True)
class SafetyResult:
    risk_level: RiskLevel
    should_short_circuit: bool
    warnings: list[str]


def safety_precheck(message: str) -> SafetyResult:
    folded = accent_fold(message)
    urgent = any(term in folded for term in URGENT_TERMS) and (
        "kho tho" in folded or "dau nguc" in folded or "co giat" in folded or "mat y thuc" in folded
    )
    if urgent:
        return SafetyResult(
            risk_level=RiskLevel.URGENT,
            should_short_circuit=True,
            warnings=["Có dấu hiệu nguy cấp. Cần liên hệ cấp cứu hoặc cơ sở y tế ngay lập tức."],
        )
    return SafetyResult(risk_level=RiskLevel.LOW, should_short_circuit=False, warnings=[])


def urgent_response() -> tuple[str, str]:
    return (
        "Nếu có khó thở, đau ngực, co giật, mất ý thức, phản vệ, ngộ độc hoặc quá liều nặng, hãy gọi cấp cứu hoặc đến cơ sở y tế gần nhất ngay lập tức.",
        "Đây là thông tin an toàn khẩn cấp, không thay thế đánh giá trực tiếp của nhân viên y tế.",
    )
