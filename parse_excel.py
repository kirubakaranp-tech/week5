import sys
from pathlib import Path

import pandas as pd

DEFAULT_FILE = Path("data") / "hr_data.xlsx"
OUTPUT_FILE = Path("output") / "excel_sentences.txt"
MERGED_COLUMNS = {"Employees": ["Department"]}


def clean_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def fill_merged_cells(sheet_name, table):
    for column in MERGED_COLUMNS.get(sheet_name, []):
        table[column] = table[column].ffill()
    return table


def row_to_text(sheet_name, row):
    if sheet_name == "Employees":
        name = row["Name"] or "An employee"
        department = row["Department"] or "an unknown department"
        if row["Salary"] is None:
            return f"Employee {name} in {department} has no salary recorded"
        return f"Employee {name} in {department} earns {row['Salary']}"

    if sheet_name == "Leaves":
        days = row["Days"]
        if days is None:
            return f"Employee {row['Employee ID']} took {row['Leave Type']} leave from {row['From']} (days not recorded)"
        day_word = "day" if days == 1 else "days"
        return f"Employee {row['Employee ID']} took {days} {day_word} of {row['Leave Type']} leave from {row['From']}"

    parts = [f"{column} is {value}" for column, value in row.items() if value is not None]
    return f"{sheet_name}: " + ", ".join(parts)


def parse_excel(path):
    sheets = pd.read_excel(path, sheet_name=None)

    print("Sheets: " + ", ".join(f"{name} {table.shape}" for name, table in sheets.items()))

    sentences = []
    for sheet_name, table in sheets.items():
        empty_before = int(table.isna().sum().sum())
        table = fill_merged_cells(sheet_name, table)
        empty_after = int(table.isna().sum().sum())
        print(f"{sheet_name}: {empty_before} empty cells, {empty_before - empty_after} filled from merged cells")

        for _, row in table.iterrows():
            clean_row = {column: clean_value(value) for column, value in row.items()}
            sentences.append(row_to_text(sheet_name, clean_row))

    return sheets, sentences


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FILE
    sheets, sentences = parse_excel(path)

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(sentences) + "\n", encoding="utf-8")

    print(f"\nSample: '{sentences[0]}'")
    print(f"Wrote {len(sentences)} sentences to {OUTPUT_FILE}")
