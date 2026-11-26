import time
from pathlib import Path

from loader import load_document

FILES = [
    "data/employee_policy.pdf",
    "data/hr_policy.docx",
    "data/hr_data.xlsx",
    "data/benefits_page.html",
]
RESULTS_FILE = Path("results") / "loader_results.md"


def main():
    rows = []
    for file in FILES:
        start = time.perf_counter()
        items = load_document(file)
        seconds = time.perf_counter() - start

        file_type = Path(file).suffix.lstrip(".")
        rows.append((file_type, Path(file).name, len(items), seconds))
        print(f"{file}: {len(items)} items in {seconds:.2f} s")
        print(f"  first item: {items[0]['page_or_section']!r} -> {items[0]['text'][:60]!r}")

    print("\nUnsupported type:")
    try:
        load_document("data/notes.txt")
    except ValueError as error:
        print(f"  ValueError: {error}")

    lines = [
        "# Unified loader results",
        "",
        "| File type | File | Items extracted | Time |",
        "|---|---|---|---|",
    ]
    for file_type, name, count, seconds in rows:
        lines.append(f"| {file_type} | {name} | {count} | {seconds:.2f} s |")

    print()
    print("\n".join(lines[2:]))

    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved the table in {RESULTS_FILE}")


if __name__ == "__main__":
    main()
