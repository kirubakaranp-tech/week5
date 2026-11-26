import os
import sys
import time
from pathlib import Path

import pymupdf as fitz
import pytesseract
from dotenv import load_dotenv
from pdf2image import convert_from_path

load_dotenv()

MIN_CHARACTERS = 20
OCR_DPI = 300
POPPLER_PATH = os.getenv("POPPLER_PATH") or None

if os.getenv("TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD")


def check_ocr_tools():
    try:
        pytesseract.get_tesseract_version()
    except pytesseract.TesseractNotFoundError:
        return f"Tesseract was not found at {pytesseract.pytesseract.tesseract_cmd}. Install it or fix TESSERACT_CMD in .env."

    if POPPLER_PATH and not (Path(POPPLER_PATH) / "pdfinfo.exe").exists():
        return f"Poppler was not found at {POPPLER_PATH}. Install it or fix POPPLER_PATH in .env."
    return None


def ocr_page(pdf_path, page_number, lang="eng"):
    images = convert_from_path(
        pdf_path,
        dpi=OCR_DPI,
        first_page=page_number,
        last_page=page_number,
        poppler_path=POPPLER_PATH,
    )
    return pytesseract.image_to_string(images[0], lang=lang)


def extract_text(pdf_path, lang="eng"):
    pages = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            number = page.number + 1
            start = time.perf_counter()

            text = page.get_text()
            method = "normal"
            if len(text.strip()) < MIN_CHARACTERS:
                text = ocr_page(pdf_path, number, lang)
                method = "ocr"

            seconds = time.perf_counter() - start
            pages.append({"page": number, "method": method, "text": text, "seconds": seconds})
    return pages


if __name__ == "__main__":
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/policy_mixed.pdf"
    lang = sys.argv[2] if len(sys.argv) > 2 else "eng"

    problem = check_ocr_tools()
    if problem:
        print(problem)
        sys.exit(1)

    print(f"Reading {pdf_path} (OCR language: {lang})\n")
    for page in extract_text(pdf_path, lang):
        first_line = next((line for line in page["text"].splitlines() if line.strip()), "")
        print(f"Page {page['page']}: {page['method']:6} | {page['seconds']:.2f} s | "
              f"{len(page['text'].strip()):4} characters | {first_line[:50]}")

    if len(sys.argv) > 2:
        print("\nText found:\n")
        print(extract_text(pdf_path, lang)[0]["text"])
