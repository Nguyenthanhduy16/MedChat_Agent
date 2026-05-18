from core.text import accent_fold, normalize_text, repair_mojibake, stable_hash, slugify


def test_normalize_text_collapses_whitespace_and_preserves_vietnamese() -> None:
    assert normalize_text("  Thuốc   dùng để làm gì? \n") == "Thuốc dùng để làm gì?"


def test_repair_mojibake_repairs_common_utf8_latin1_corruption() -> None:
    repaired, changed, confidence = repair_mojibake("DÆ°á»£c cháº¥t Long ChÃ¢u")
    assert changed is True
    assert confidence >= 0.8
    assert "Dược chất" in repaired
    assert "Long Châu" in repaired


def test_repair_mojibake_repairs_double_encoded_utf8_latin1_corruption() -> None:
    double_encoded = "Dược chất Long Châu".encode("utf-8").decode("latin1").encode("utf-8").decode("latin1")

    repaired, changed, confidence = repair_mojibake(double_encoded)

    assert changed is True
    assert confidence >= 0.8
    assert repaired == "Dược chất Long Châu"


def test_accent_fold_supports_sparse_matching() -> None:
    assert accent_fold("Phụ nữ mang thai dùng thuốc") == "phu nu mang thai dung thuoc"


def test_slugify_and_hash_are_stable() -> None:
    assert slugify("Dược chất Long Châu") == "duoc-chat-long-chau"
    assert stable_hash("abc") == "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert stable_hash("abc") == stable_hash("abc")
    assert stable_hash("abc") != stable_hash("abcd")
