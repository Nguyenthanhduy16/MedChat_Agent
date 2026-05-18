import hashlib
import re
import unicodedata


MOJIBAKE_MARKERS = ("\u00c3", "\u00c6", "\u00e1\u00bb", "\u00e1\u00ba", "\u00c2", "\u00c4")


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    normalized = re.sub(r"[ \t\r\n\f\v]+", " ", normalized)
    return normalized.strip()


def repair_mojibake(value: str) -> tuple[str, bool, float]:
    text = normalize_text(value)
    marker_count = _mojibake_marker_count(text)
    if marker_count == 0:
        return text, False, 1.0

    repaired = text
    repaired_marker_count = marker_count
    for _ in range(3):
        candidate = normalize_text(_decode_mojibake_once(repaired))
        candidate_marker_count = _mojibake_marker_count(candidate)
        if candidate == repaired or candidate_marker_count >= repaired_marker_count:
            break
        repaired = candidate
        repaired_marker_count = candidate_marker_count
        if repaired_marker_count == 0:
            break

    if repaired == text:
        return text, False, 0.0
    if repaired_marker_count == 0:
        confidence = 0.9
    elif repaired_marker_count <= marker_count / 2:
        confidence = 0.7
    else:
        confidence = 0.4
    return repaired, repaired != text, confidence


def _mojibake_marker_count(value: str) -> int:
    return sum(value.count(marker) for marker in MOJIBAKE_MARKERS)


def _decode_mojibake_once(value: str) -> str:
    for encoding in ("cp1252", "latin1"):
        try:
            return value.encode(encoding).decode("utf-8")
        except UnicodeError:
            continue
    return value


def accent_fold(value: str) -> str:
    repaired = _fully_repair_mojibake(value)
    normalized = unicodedata.normalize("NFD", repaired)
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    without_marks = without_marks.replace("\u0111", "d").replace("\u0110", "D")
    lowered = without_marks.lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _fully_repair_mojibake(value: str) -> str:
    repaired = normalize_text(value)
    for _ in range(3):
        next_value, changed, _ = repair_mojibake(repaired)
        if not changed:
            return next_value
        repaired = next_value
    return repaired


def slugify(value: str) -> str:
    folded = accent_fold(value)
    return re.sub(r"\s+", "-", folded).strip("-")


def stable_hash(value: str) -> str:
    """Return a stable hash of the exact input; normalize before calling when normalized identity is needed."""
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()
