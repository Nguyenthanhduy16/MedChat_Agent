"""Input normalization — bước đầu tiên trong flow."""

import re

from core.models import NormalizedInput
from core.text import accent_fold, normalize_text


_VI_DIACRITIC_RE = re.compile(
    r"[àáảãạăắặằẵẳâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ"
    r"ÀÁẢÃẠĂẮẶẰẴẲÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ]"
)

_SPLIT_RE = re.compile(r"[?;]\s*|\s+(?:và|hay|hoặc|ngoài ra|thêm nữa)\s+", re.IGNORECASE)

def normalize_input(message: str) -> NormalizedInput:
    original = message.strip()
    normalized = accent_fold(normalize_text(original))
    language = _detect_language(original)
    question_parts = _split_question_parts(original)
    return NormalizedInput(
        original=original,
        normalized=normalized,
        language=language,
        question_parts=question_parts,
    )

def _detect_language(text: str) -> str:
    if _VI_DIACRITIC_RE.search(text):
        return "vi"
    folded = accent_fold(text).lower()
    vi_signals = sum(1 for w in ("thuoc", "benh", "dung", "uong", "lieu") if w in folded)
    if vi_signals >= 2:
        return "vi"
    en_signals = sum(1 for w in ("dose", "drug", "renal", "tablet", "mg", "ml") if w in folded)
    if vi_signals >= 1 and en_signals >= 1:
        return "mixed"
    if en_signals >= 2:
        return "en"
    return "vi"

def _split_question_parts(text: str) -> list[str]:
    raw_parts = _SPLIT_RE.split(text)
    parts = [p.strip() for p in raw_parts if len(p.strip()) > 8]
    return parts if len(parts) > 1 else [text.strip()]
