import random
from pathlib import Path

from docx import Document
from openpyxl import Workbook

FOLDER = Path("docs_to_ingest")


def change_leave_docx():
    path = FOLDER / "leave.docx"
    doc = Document(path)
    doc.add_heading("Leave During Notice Period", level=1)
    doc.add_paragraph(
        "Employees who are serving their notice period can take earned leave only with approval "
        "from their manager. Leave taken during the notice period does not extend the last working day."
    )
    doc.save(path)
    print(f"Changed {path}: added the section 'Leave During Notice Period'")


def create_new_xlsx():
    path = FOLDER / "new.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.title = "Training"
    sheet.append(["Employee ID", "Course", "Hours"])
    courses = ["Python basics", "Data security", "Customer care", "Excel for HR", "Leadership"]
    random.seed(3)
    for number in range(1, 31):
        sheet.append([f"E{number:03}", random.choice(courses), random.choice([2, 4, 6, 8])])
    book.save(path)
    print(f"Created {path} with 30 rows")


if __name__ == "__main__":
    change_leave_docx()
    create_new_xlsx()
