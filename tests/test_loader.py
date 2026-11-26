import pytest

import parse_html
from loader import load_document
from parse_html import fetch_page, html_to_text

PAGE = """
<html><head><title>Benefits</title><script>var tracking = 1;</script><style>p {color: red}</style></head>
<body>
<nav><a href="/">Home</a> <a href="/careers">Careers</a></nav>
<h1>Benefits</h1><p>Health cover of Rs 5 lakh.</p>
<h2>Learning</h2><p>Rs 40,000 a year for courses.</p>
<footer>Copyright 2026</footer>
<script>console.log("loaded")</script>
</body></html>
"""


def test_nav_scripts_and_footer_are_removed():
    text = html_to_text(PAGE)
    assert "Health cover of Rs 5 lakh." in text
    assert "Careers" not in text
    assert "tracking" not in text
    assert "console.log" not in text
    assert "color: red" not in text
    assert "Copyright" not in text


def test_fetch_page_uses_requests(monkeypatch):
    calls = []

    class FakeResponse:
        text = PAGE

        def raise_for_status(self):
            pass

    def fake_get(url, timeout, headers):
        calls.append((url, timeout))
        return FakeResponse()

    monkeypatch.setattr(parse_html.requests, "get", fake_get)

    assert fetch_page("https://example.com/benefits") == PAGE
    assert calls == [("https://example.com/benefits", 15)]


@pytest.mark.parametrize(
    "file, count, first_section",
    [
        ("data/employee_policy.pdf", 12, 1),
        ("data/hr_policy.docx", 11, "Start"),
        ("data/hr_data.xlsx", 470, "Employees row 2"),
        ("data/benefits_page.html", 6, "Start"),
    ],
)
def test_load_document_on_each_type(file, count, first_section):
    items = load_document(file)

    assert len(items) == count
    assert items[0]["page_or_section"] == first_section
    for item in items:
        assert set(item) == {"text", "source", "page_or_section"}
        assert item["text"].strip()
        assert item["source"] == file.split("/")[-1]


def test_sections_follow_the_headings():
    docx_sections = [item["page_or_section"] for item in load_document("data/hr_policy.docx")]
    assert "Leave Rules" in docx_sections
    assert docx_sections[-2:] == ["Table 1", "Table 2"]

    html_items = load_document("data/benefits_page.html")
    learning = [item for item in html_items if item["page_or_section"] == "Learning Budget"][0]
    assert "Rs 40,000" in learning["text"]
    assert all("Privacy policy" not in item["text"] for item in html_items)


def test_excel_items_are_rag_sentences():
    assert load_document("data/hr_data.xlsx")[0]["text"] == "Employee Arun in Sales earns 30000"


def test_unsupported_type_gives_a_clear_error():
    with pytest.raises(ValueError, match=r"Unsupported file type '\.txt'.*Supported types: pdf, docx, xlsx, html"):
        load_document("data/notes.txt")


def test_missing_file_gives_a_clear_error():
    with pytest.raises(FileNotFoundError, match="File not found"):
        load_document("data/missing.pdf")


def test_extension_case_does_not_matter(tmp_path):
    page = tmp_path / "PAGE.HTM"
    page.write_text(PAGE, encoding="utf-8")
    assert load_document(page)[0]["source"] == "PAGE.HTM"
