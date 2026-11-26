import pytest

import ocr_pdf
from compare_ocr import get_words, word_accuracy
from ocr_pdf import check_ocr_tools, extract_text

ocr_tools_missing = check_ocr_tools()


def test_digital_pages_use_normal_extraction_and_scanned_pages_use_ocr(monkeypatch):
    ocr_calls = []

    def fake_ocr(pdf_path, page_number, lang="eng"):
        ocr_calls.append((page_number, lang))
        return f"text read by OCR from page {page_number}"

    monkeypatch.setattr(ocr_pdf, "ocr_page", fake_ocr)

    pages = extract_text("data/policy_mixed.pdf")

    assert [page["method"] for page in pages] == ["normal", "normal", "ocr", "ocr"]
    assert ocr_calls == [(3, "eng"), (4, "eng")]
    assert "Employee Policy Handbook" in pages[0]["text"]
    assert pages[2]["text"] == "text read by OCR from page 3"


def test_ocr_language_is_passed_on(monkeypatch):
    languages = []
    monkeypatch.setattr(ocr_pdf, "ocr_page", lambda pdf, page, lang="eng": languages.append(lang) or "x" * 30)

    extract_text("data/tamil_english.pdf", lang="eng+tam")

    assert languages == ["eng+tam"]


def test_get_words_ignores_case_and_punctuation():
    assert get_words("Sick leave: 10 days, NOT allowed!") == ["sick", "leave", "10", "days", "not", "allowed"]


def test_word_accuracy():
    matched, total, missed = word_accuracy("earned leave 18 days, sick leave 10 days", "earned leave 18 days sickleave 10 days")
    assert (matched, total) == (6, 8)
    assert missed == ["leave", "sick"]


@pytest.mark.skipif(bool(ocr_tools_missing), reason=str(ocr_tools_missing))
def test_real_ocr_on_the_scanned_page():
    pages = extract_text("data/policy_mixed.pdf")
    assert pages[2]["method"] == "ocr"
    assert "Leave Policy" in pages[2]["text"]
    assert "medical certificate" in pages[2]["text"]
