import json
import sys
import time
from collections import Counter
from pathlib import Path

import pymupdf as fitz

DEFAULT_PDF = Path("data") / "employee_policy.pdf"
OUTPUT_FOLDER = Path("output") / "pages"
HEADING_SCALE = 1.3


def get_body_font_size(doc):
    sizes = Counter()
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    sizes[round(span["size"], 1)] += len(span["text"].strip())
    return sizes.most_common(1)[0][0]


def find_headings(page, body_size):
    headings = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            if not line["spans"]:
                continue
            text = "".join(span["text"] for span in line["spans"]).strip()
            size = max(span["size"] for span in line["spans"])
            if text and size >= body_size * HEADING_SCALE:
                headings.append(text)
    return headings


def show_first_blocks(page, count=3):
    print(f"First {count} blocks of page 1:")
    for x0, y0, x1, y1, text, block_number, block_type in page.get_text("blocks")[:count]:
        short_text = " ".join(text.split())[:70]
        print(f"  Block {block_number}: ({x0:.0f}, {y0:.0f}, {x1:.0f}, {y1:.0f}) {short_text}")


def extract_pdf(pdf_path, output_folder=OUTPUT_FOLDER):
    start = time.perf_counter()
    doc = fitz.open(pdf_path)
    body_size = get_body_font_size(doc)
    output_folder.mkdir(parents=True, exist_ok=True)

    show_first_blocks(doc[0])
    print(f"Body font size: {body_size} | heading font size: {body_size * HEADING_SCALE:.1f} or more\n")

    all_headings = []
    for page in doc:
        page_start = time.perf_counter()
        number = page.number + 1

        text = page.get_text()
        headings = find_headings(page, body_size)
        record = {"source": Path(pdf_path).name, "page": number, "text": text, "headings": headings}

        json_file = output_folder / f"page_{number:02}.json"
        json_file.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")

        for heading in headings:
            all_headings.append((heading, number))

        page_time = time.perf_counter() - page_start
        print(f"Page {number:2}: {page_time:.3f} s | {len(text):5} characters | headings: {headings}")

    total_time = time.perf_counter() - start
    page_count = doc.page_count
    doc.close()
    return page_count, total_time, all_headings


if __name__ == "__main__":
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    page_count, total_time, headings = extract_pdf(pdf_path)

    print()
    print(f"Pages: {page_count} | Time: {total_time:.2f} s")
    print(f"Headings: {headings}")
    print(f"Saved one JSON file per page in {OUTPUT_FOLDER}")
