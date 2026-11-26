import re
from collections import Counter
from pathlib import Path

import pymupdf as fitz

from ocr_pdf import check_ocr_tools, extract_text

ORIGINAL_PDF = "data/employee_policy.pdf"
ORIGINAL_PAGE = 3
SCANNED_PDF = "data/policy_mixed.pdf"
SCANNED_PAGE = 3
RESULTS_FILE = Path("results") / "ocr_comparison.md"


def get_words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def word_accuracy(original_text, ocr_text):
    original_words = Counter(get_words(original_text))
    ocr_words = Counter(get_words(ocr_text))
    matched = sum((original_words & ocr_words).values())
    total = sum(original_words.values())
    missed = sorted((original_words - ocr_words).elements())
    return matched, total, missed


def main():
    problem = check_ocr_tools()
    if problem:
        print(problem)
        return

    with fitz.open(ORIGINAL_PDF) as doc:
        original_text = doc[ORIGINAL_PAGE - 1].get_text()

    scanned_page = extract_text(SCANNED_PDF)[SCANNED_PAGE - 1]
    ocr_text = scanned_page["text"]

    matched, total, missed = word_accuracy(original_text, ocr_text)
    accuracy = matched / total * 100

    print(f"Original: {ORIGINAL_PDF} page {ORIGINAL_PAGE} (normal extraction)")
    print(f"Scanned:  {SCANNED_PDF} page {SCANNED_PAGE} (read with {scanned_page['method']})")
    print(f"Word match: {matched}/{total} words ({accuracy:.1f}%)")
    print(f"Missed or misread words: {missed if missed else 'none'}")

    lines = [
        "# Normal extraction vs OCR",
        "",
        f"- Original: `{ORIGINAL_PDF}`, page {ORIGINAL_PAGE}, read with PyMuPDF",
        f"- Scanned: `{SCANNED_PDF}`, page {SCANNED_PAGE}, read with {scanned_page['method']} (pdf2image and pytesseract)",
        f"- Word match: **{matched}/{total} words ({accuracy:.1f}%)**",
        f"- Missed or misread words: {', '.join(missed) if missed else 'none'}",
        "",
        "## Normal extraction",
        "",
        "```",
        original_text.strip(),
        "```",
        "",
        "## OCR",
        "",
        "```",
        ocr_text.strip(),
        "```",
        "",
    ]
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSaved both texts side by side in {RESULTS_FILE}")


if __name__ == "__main__":
    main()
