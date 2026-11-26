import pandas as pd
from docx import Document

from parse_docx import parse_docx, read_table, table_to_dicts
from parse_excel import clean_value, fill_merged_cells, parse_excel, row_to_text


def test_word_file_has_8_headings_and_2_tables():
    headings, tables = parse_docx("data/hr_policy.docx")
    assert len(headings) == 8
    assert headings[0] == "Purpose"
    assert len(tables) == 2
    assert tables[0][0]["Leave type"] == "Earned leave"


def test_merged_word_cell_is_found_and_keeps_its_text():
    doc = Document("data/hr_policy.docx")
    rows, merged_cells = read_table(doc.tables[0])
    assert merged_cells == 1
    assert rows[2][2] == rows[3][2] == "Not allowed"


def test_empty_cells_and_repeated_headers():
    records = table_to_dicts([["Name", "", "Name"], ["Arun", "x", ""]])
    assert records == [{"Name": "Arun", "Column 2": "x", "Name 3": None}]


def test_excel_sheets_and_sample_sentence(tmp_path):
    sheets, sentences = parse_excel("data/hr_data.xlsx")
    assert {name: table.shape for name, table in sheets.items()} == {"Employees": (120, 5), "Leaves": (350, 4)}
    assert sentences[0] == "Employee Arun in Sales earns 30000"
    assert len(sentences) == 470


def test_merged_excel_cells_are_filled_from_above():
    table = pd.DataFrame({"Name": ["Arun", "Ravi", "Meena"], "Department": ["Sales", None, "HR"]})
    filled = fill_merged_cells("Employees", table)
    assert list(filled["Department"]) == ["Sales", "Sales", "HR"]


def test_clean_value():
    assert clean_value(float("nan")) is None
    assert clean_value(30000.0) == 30000
    assert clean_value(pd.Timestamp("2026-03-12")) == "2026-03-12"


def test_row_to_text_with_empty_cells():
    assert row_to_text("Employees", {"Name": "Ravi", "Department": None, "Salary": None}) == \
        "Employee Ravi in an unknown department has no salary recorded"
    assert row_to_text("Leaves", {"Employee ID": "E007", "Leave Type": "Sick", "From": "2026-02-03", "Days": 1}) == \
        "Employee E007 took 1 day of Sick leave from 2026-02-03"
    assert row_to_text("Assets", {"Item": "Laptop", "Owner": None}) == "Assets: Item is Laptop"
