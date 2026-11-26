from pathlib import Path

import pandas as pd
from docx import Document

from ocr_pdf import extract_text
from parse_excel import clean_value, fill_merged_cells, row_to_text
from parse_html import clean_html

SUPPORTED_TYPES = ["pdf", "docx", "xlsx", "html"]


def load_pdf(path):
    items = []
    for page in extract_text(path):
        if page["text"].strip():
            items.append({"text": page["text"].strip(), "source": path.name, "page_or_section": page["page"]})
    return items


def load_docx(path):
    doc = Document(path)
    items = []
    section = "Start"
    lines = []

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        if paragraph.style.name.startswith("Heading"):
            if lines:
                items.append({"text": "\n".join(lines), "source": path.name, "page_or_section": section})
            section = text
            lines = [text]
        else:
            lines.append(text)
    if lines:
        items.append({"text": "\n".join(lines), "source": path.name, "page_or_section": section})

    for number, table in enumerate(doc.tables, start=1):
        rows = []
        for r in range(len(table.rows)):
            cells = [table.cell(r, c).text.strip() for c in range(len(table.columns))]
            rows.append(" | ".join(cells))
        items.append({"text": "\n".join(rows), "source": path.name, "page_or_section": f"Table {number}"})

    return items


def load_xlsx(path):
    items = []
    for sheet_name, table in pd.read_excel(path, sheet_name=None).items():
        table = fill_merged_cells(sheet_name, table)
        for index, row in table.iterrows():
            clean_row = {column: clean_value(value) for column, value in row.items()}
            items.append({
                "text": row_to_text(sheet_name, clean_row),
                "source": path.name,
                "page_or_section": f"{sheet_name} row {index + 2}",
            })
    return items


def load_html(path):
    soup = clean_html(path.read_text(encoding="utf-8"))
    headings = [heading.get_text(strip=True) for heading in soup.find_all(["h1", "h2", "h3"])]
    text = soup.get_text(separator="\n", strip=True)

    items = []
    section = "Start"
    lines = []
    for line in text.splitlines():
        if line in headings:
            if lines:
                items.append({"text": "\n".join(lines), "source": path.name, "page_or_section": section})
            section = line
            lines = [line]
        else:
            lines.append(line)
    if lines:
        items.append({"text": "\n".join(lines), "source": path.name, "page_or_section": section})
    return items


def load_document(path):
    path = Path(path)
    file_type = path.suffix.lower().lstrip(".")
    if file_type == "htm":
        file_type = "html"

    if file_type not in SUPPORTED_TYPES:
        raise ValueError(
            f"Unsupported file type '.{file_type}' for {path.name}. Supported types: {', '.join(SUPPORTED_TYPES)}"
        )
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if file_type == "pdf":
        return load_pdf(path)
    if file_type == "docx":
        return load_docx(path)
    if file_type == "xlsx":
        return load_xlsx(path)
    return load_html(path)
