"""Rule-based Post Verifier."""

import re
from dataclasses import dataclass
from core.models import EvidenceStatus, RiskLevel
from core.evidence_gate import EvidenceCoverage

@dataclass
class VerifyResult:
    passed: bool
    failures: list[str]

def verify_answer(
    answer: str,
    coverage: EvidenceCoverage,
    risk_level: RiskLevel,
    citations: list[dict],
) -> VerifyResult:
    failures: list[str] = []
    
    if citations:
        if not re.search(r"\[S\d+\]", answer):
            failures.append("Missing citations: The answer does not contain any [S#] markers.")
            
    if coverage.status in {EvidenceStatus.WEAK_PARTIAL, EvidenceStatus.INSUFFICIENT}:
        hallucination_triggers = ["an toàn", "được dùng", "sử dụng được", "hoàn toàn", "liều"]
        lower_answer = answer.lower()
        if any(trigger in lower_answer for trigger in hallucination_triggers):
            if "không " not in lower_answer and "chưa " not in lower_answer:
                failures.append("Hallucination guard: Answer seems too definitive for weak evidence.")

    if risk_level in {RiskLevel.HIGH, RiskLevel.URGENT}:
        advice_triggers = ["bác sĩ", "dược sĩ", "y tế", "chuyên gia", "bệnh viện"]
        if not any(trigger in answer.lower() for trigger in advice_triggers):
            failures.append("Missing high-risk advice: No recommendation to consult a medical professional.")

    if coverage.status in {EvidenceStatus.USABLE_PARTIAL, EvidenceStatus.WEAK_PARTIAL}:
        missing_triggers = ["chưa đủ", "thiếu", "không có", "không tìm thấy", "hạn chế", "một phần"]
        if not any(trigger in answer.lower() for trigger in missing_triggers):
            failures.append("Missing evidence caveat: Did not mention that evidence is partial.")

    return VerifyResult(passed=len(failures) == 0, failures=failures)
