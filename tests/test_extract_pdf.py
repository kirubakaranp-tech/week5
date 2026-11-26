import json

import pymupdf as fitz

from extract_pdf import extract_pdf, find_headings, get_body_font_size


def make_pdf(path):
    doc = fitz.open()
    for title in ["Leave Policy", None, "Attendance"]:
        page = doc.new_page()
        y = 72
        if title:
            page.insert_text((72, y), title, fontsize=18)
            y += 30
        for number in range(8):
            page.insert_text((72, y), f"This is a normal line of policy text number {number}.", fontsize=10)
            y += 14
        page.insert_text((72, y + 10), "A small bold-looking subheading", fontsize=11)
    doc.save(path)
    doc.close()


def test_body_font_size_is_the_most_common_size(tmp_path):
    pdf = tmp_path / "policy.pdf"
    make_pdf(pdf)
    with fitz.open(pdf) as doc:
        assert get_body_font_size(doc) == 10


def test_only_big_text_counts_as_a_heading(tmp_path):
    pdf = tmp_path / "policy.pdf"
    make_pdf(pdf)
    with fitz.open(pdf) as doc:
        assert find_headings(doc[0], 10) == ["Leave Policy"]
        assert find_headings(doc[1], 10) == []


def test_extract_pdf_saves_one_json_per_page(tmp_path, capsys):
    pdf = tmp_path / "policy.pdf"
    make_pdf(pdf)
    output = tmp_path / "pages"

    page_count, total_time, headings = extract_pdf(pdf, output)

    assert page_count == 3
    assert total_time > 0
    assert headings == [("Leave Policy", 1), ("Attendance", 3)]

    files = sorted(output.glob("*.json"))
    assert [file.name for file in files] == ["page_01.json", "page_02.json", "page_03.json"]

    page_one = json.loads(files[0].read_text(encoding="utf-8"))
    assert page_one["source"] == "policy.pdf"
    assert page_one["page"] == 1
    assert "normal line of policy text" in page_one["text"]
    assert page_one["headings"] == ["Leave Policy"]

    printed = capsys.readouterr().out
    assert "First 3 blocks of page 1:" in printed
    assert "Block 2:" in printed
    assert "Page  3:" in printed


def test_real_policy_pdf():
    with fitz.open("data/employee_policy.pdf") as doc:
        assert doc.page_count >= 10
        body = get_body_font_size(doc)
        assert find_headings(doc[2], body) == ["Leave Policy"]
        assert find_headings(doc[4], body) == ["Attendance"]
