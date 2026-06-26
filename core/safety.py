from dataclasses import dataclass
import re

from core.models import RiskLevel
from core.text import accent_fold


# ---------------------------------------------------------------------------
# Các cụm từ chỉ dấu hiệu nguy cấp (đã fold accent)
# ---------------------------------------------------------------------------
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

# Các từ nguy cấp TỐI THIỂU phải có để trigger (ít nhất 1 trong số này)
_MUST_HAVE_TERMS = frozenset({"kho tho", "dau nguc", "co giat", "mat y thuc"})

# ---------------------------------------------------------------------------
# Negative context: nếu câu chứa các pattern này thì là câu hỏi tra cứu,
# KHÔNG phải tình trạng khẩn cấp → bỏ qua trigger
# ---------------------------------------------------------------------------
# Các pattern chỉ ngữ cảnh đặt câu hỏi / tra cứu thông tin
_QUERY_CONTEXT_PATTERNS: tuple[str, ...] = (
    # dạng "có ... không", "có gây ... không", "có làm ... không"
    r"co\s+(?:\w+\s+){0,5}(kho tho|dau nguc|co giat|mat y thuc|phan ve|qua lieu|ngo doc)",
    # "gây khó thở", "gây đau ngực", v.v.
    r"gay\s+(kho tho|dau nguc|co giat|mat y thuc|phan ve|qua lieu|ngo doc)",
    # "làm khó thở", "làm đau ngực"
    r"lam\s+(kho tho|dau nguc|co giat|mat y thuc)",
    # "dẫn đến", "dẫn tới", "khiến"
    r"(?:dan den|dan toi|khien)\s+(kho tho|dau nguc|co giat|mat y thuc)",
    # "triệu chứng", "tác dụng phụ", "tác dụng", "tác hại"
    r"(?:trieu chung|tac dung phu|tac dung|tac hai|phan ung phu|phan ung)",
    # "có thể gây", "có thể dẫn"
    r"co the\s+(?:gay|dan|lam|khien)",
    # "nguy cơ", "rủi ro", "khả năng"
    r"(?:nguy co|rui ro|kha nang)\s+(?:gay|dan|lam)",
    # "thuốc ... có ... không", "thuốc nào gây"
    r"thuoc\s+\w+.*\s+co\b",
    r"thuoc\s+nao\s+(?:gay|dan|lam|khien|co the)",
    # "liều nào gây", "liều bao nhiêu thì"
    r"(?:lieu|ham luong)\s+(?:nao|bao nhieu)\s+(?:thi\s+)?(?:gay|dan|co the)",
    # "bị ... khi dùng", "xảy ra khi", "khi nào thì"
    r"(?:bi|xay ra)\s+khi\s+(?:dung|uong|su dung|dung thuoc)",
    # "điều trị", "xử lý", "xử trí", "phòng ngừa" + từ nguy cấp
    r"(?:dieu tri|xu ly|xu tri|phong ngua|cach phong|cach xu|kiem soat)\s+\w+",
    # "cần xử trí", "cần làm gì", "cần gọi" — câu hỏi hướng dẫn xử lý
    r"can\s+(?:xu tri|xu ly|lam gi|goi|den|cap cuu)",
    # "thông tin về", "tra cứu", "hỏi về", "biết về"
    r"(?:thong tin|tra cuu|hoi ve|biet ve|giai thich|mo ta)\s+",
    # "khi nào cần", "khi nào phải"
    r"khi nao\s+(?:can|phai|nen|goi|den)",
    # Câu hỏi dạng "... không?" ở cuối câu
    r"(?:kho tho|dau nguc|co giat|mat y thuc)\s+khong\s*\??$",
    # "không ảnh hưởng", "không gây", phủ định
    r"khong\s+(?:gay|lam|dan|anh huong)",
    # "có an toàn", "an toàn không"
    r"an toan\s+khong|co\s+an toan",
)

# Compile để tái sử dụng
_COMPILED_QUERY_PATTERNS = [re.compile(p) for p in _QUERY_CONTEXT_PATTERNS]


# ---------------------------------------------------------------------------
# Positive context: các pattern chỉ tình trạng ĐANG XẢY RA (tăng độ tin cậy)
# ---------------------------------------------------------------------------
_EMERGENCY_CONTEXT_PATTERNS: tuple[str, ...] = (
    # "tôi đang", "em đang", "mình đang" + từ nguy cấp
    r"(?:toi|em|minh|anh|chi|ba|ong|con|chau)\s+(?:dang|bi|vua)\s+",
    # "đột ngột", "bỗng nhiên", "ngay lập tức"
    r"(?:dot ngot|bong nhien|bat ngo|ngay lap tuc)\s+(?:bi|gap)\s+",
    # "cấp cứu", "nguy hiểm tính mạng"
    r"(?:cap cuu|nguy hiem tinh mang|nguy kich|nguy cap)",
    # "không thở được", "ngất xỉu", "ngất đi"
    r"(?:khong tho duoc|ngat xiu|ngat di|bat tinh)",
    # "gọi 115", "gọi cấp cứu"
    r"(?:goi 115|goi cap cuu)",
    # "đang xảy ra", "hiện tại"
    r"(?:dang xay ra|hien tai|luc nay|bay gio)\s+",
    # "bệnh nhân", "người thân" + đang
    r"(?:benh nhan|nguoi than|nguoi nha)\s+(?:dang|bi|vua)\s+",
    # Dấu hiệu mô tả khẩn cấp: "mạch nhanh", "tím tái", "co cứng"
    r"(?:mach nhanh|tim tai|co cung|sung phu|kho nuot|hat mau|noi mau)",
)

_COMPILED_EMERGENCY_PATTERNS = [re.compile(p) for p in _EMERGENCY_CONTEXT_PATTERNS]


@dataclass(frozen=True)
class SafetyResult:
    risk_level: RiskLevel
    should_short_circuit: bool
    warnings: list[str]


def _is_query_context(folded: str) -> bool:
    """Trả về True nếu câu là ngữ cảnh tra cứu thông tin (không phải khẩn cấp thực sự)."""
    return any(p.search(folded) for p in _COMPILED_QUERY_PATTERNS)


def _has_emergency_context(folded: str) -> bool:
    """Trả về True nếu câu có dấu hiệu tình trạng đang xảy ra khẩn cấp."""
    return any(p.search(folded) for p in _COMPILED_EMERGENCY_PATTERNS)


def safety_precheck(message: str) -> SafetyResult:
    """
    Kiểm tra an toàn trước khi xử lý tin nhắn.

    Logic phân tầng:
    1. Nếu không chứa từ nguy cấp → LOW, tiếp tục bình thường.
    2. Nếu chứa từ nguy cấp VÀ có ngữ cảnh khẩn cấp rõ ràng → URGENT, short-circuit.
    3. Nếu chứa từ nguy cấp NHƯNG là ngữ cảnh tra cứu → HIGH (cảnh báo nhẹ), tiếp tục.
    4. Nếu chứa từ nguy cấp nhưng không rõ ngữ cảnh → URGENT, short-circuit (an toàn là trên hết).
    """
    folded = accent_fold(message)

    # Bước 1: Không có từ nguy cấp nào → bình thường
    matched_terms = [term for term in URGENT_TERMS if term in folded]
    if not matched_terms:
        return SafetyResult(risk_level=RiskLevel.LOW, should_short_circuit=False, warnings=[])

    # Bước 2: Phải có ít nhất 1 từ trong nhóm "must have" mới trigger
    has_must_have = any(term in folded for term in _MUST_HAVE_TERMS)
    if not has_must_have:
        # Chỉ chứa "qua lieu", "ngo doc", "tu tu", "phan ve" → cần kiểm tra ngữ cảnh riêng
        # Nếu là ngữ cảnh tra cứu → không short-circuit
        if _is_query_context(folded):
            return SafetyResult(
                risk_level=RiskLevel.HIGH,
                should_short_circuit=False,
                warnings=[f"Câu hỏi đề cập đến '{', '.join(matched_terms)}'. Nếu đây là tình trạng khẩn cấp, hãy gọi cấp cứu ngay."],
            )
        # Ngữ cảnh không rõ → trigger an toàn
        return SafetyResult(
            risk_level=RiskLevel.URGENT,
            should_short_circuit=True,
            warnings=["Có dấu hiệu nguy cấp. Cần liên hệ cấp cứu hoặc cơ sở y tế ngay lập tức."],
        )

    # Bước 3: Có từ "must have" → kiểm tra ngữ cảnh
    is_query = _is_query_context(folded)
    is_emergency = _has_emergency_context(folded)

    if is_emergency and not is_query:
        # Rõ ràng là khẩn cấp
        return SafetyResult(
            risk_level=RiskLevel.URGENT,
            should_short_circuit=True,
            warnings=["Có dấu hiệu nguy cấp. Cần liên hệ cấp cứu hoặc cơ sở y tế ngay lập tức."],
        )

    if is_query and not is_emergency:
        # Rõ ràng là tra cứu → tiếp tục xử lý bình thường, chỉ thêm cảnh báo nhẹ
        return SafetyResult(
            risk_level=RiskLevel.HIGH,
            should_short_circuit=False,
            warnings=[
                "Câu hỏi đề cập đến các triệu chứng nguy cấp. "
                "Nếu đây là tình trạng đang xảy ra, hãy gọi cấp cứu ngay lập tức."
            ],
        )

    if is_query and is_emergency:
        # Cả hai dấu hiệu → ưu tiên an toàn, trigger khẩn cấp
        return SafetyResult(
            risk_level=RiskLevel.URGENT,
            should_short_circuit=True,
            warnings=["Có dấu hiệu nguy cấp. Cần liên hệ cấp cứu hoặc cơ sở y tế ngay lập tức."],
        )

    # Bước 4: Không xác định được ngữ cảnh → trigger an toàn (thà cảnh báo nhầm)
    return SafetyResult(
        risk_level=RiskLevel.URGENT,
        should_short_circuit=True,
        warnings=["Có dấu hiệu nguy cấp. Cần liên hệ cấp cứu hoặc cơ sở y tế ngay lập tức."],
    )


def urgent_response() -> tuple[str, str]:
    return (
        "Nếu có khó thở, đau ngực, co giật, mất ý thức, phản vệ, ngộ độc hoặc quá liều nặng, hãy gọi cấp cứu hoặc đến cơ sở y tế gần nhất ngay lập tức.",
        "Đây là thông tin an toàn khẩn cấp, không thay thế đánh giá trực tiếp của nhân viên y tế.",
    )
