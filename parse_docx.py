import json
import sys
from pathlib import Path

from docx import Document

DEFAULT_FILE = Path("data") / "hr_policy.docx"
OUTPUT_FILE = Path("output") / "docx_tables.json"


def show_paragraphs(doc):
    headings = []
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style = paragraph.style.name
        print(f"[{style}] {text}")
        if style.startswith("Heading"):
            headings.append(text)
    return headings


def read_table(table):
    rows = []
    merged_cells = 0
    for r in range(len(table.rows)):
        row = []
        for c in range(len(table.columns)):
            cell = table.cell(r, c)
            if r > 0 and cell._tc is table.cell(r - 1, c)._tc:
                merged_cells += 1
            row.append(cell.text.strip())
        rows.append(row)
    return rows, merged_cells


def table_to_dicts(rows):
    headers = []
    for number, header in enumerate(rows[0], start=1):
        name = header or f"Column {number}"
        if name in headers:
            name = f"{name} {number}"
        headers.append(name)

    records = []
    for row in rows[1:]:
        record = {}
        for header, value in zip(headers, row):
            record[header] = value if value else None
        records.append(record)
    return records


def parse_docx(path):
    doc = Document(path)

    print("Paragraphs:")
    headings = show_paragraphs(doc)

    tables = []
    for number, table in enumerate(doc.tables, start=1):
        rows, merged_cells = read_table(table)
        records = table_to_dicts(rows)
        tables.append(records)

        print(f"\nTable {number}: {len(rows)} rows x {len(rows[0])} columns, {merged_cells} merged cell(s)")
        for record in records:
            print(f"  {record}")

    return headings, tables


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FILE
    headings, tables = parse_docx(path)

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(tables, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(f"Headings found: {len(headings)} | Tables: {len(tables)}")
    print(f"Saved the tables as lists of dictionaries in {OUTPUT_FILE}")
