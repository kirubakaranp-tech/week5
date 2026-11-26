# Enterprise Document Processing

Reading company documents for RAG: digital PDFs with PyMuPDF and, later, scanned PDFs with OCR.

## Task 1: Digital PDF extraction

The input is `data/employee_policy.pdf`, a 12-page employee policy handbook.

`extract_pdf.py` does the following:

1. Opens the PDF with PyMuPDF (`fitz`) and reads the text of every page.
2. Prints the first 3 layout blocks of page 1 from `page.get_text("blocks")`, with their position on the page.
3. Finds headings by font size. It reads every line with `page.get_text("dict")`, takes the most
   common font size as the body text size, and treats a line as a heading when its font is at
   least 1.3 times bigger. That gives a list of `(heading, page)`.
4. Saves each page as JSON in `output/pages/`, for example `page_03.json`:

   ```json
   {"source": "employee_policy.pdf", "page": 3, "text": "...", "headings": ["Leave Policy"]}
   ```

5. Prints the extraction time for every page and the total time.

## Setup

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Run

```
python extract_pdf.py
```

To read another PDF, give its path: `python extract_pdf.py path\to\file.pdf`.

The output ends like this:

```
Pages: 12 | Time: 0.03 s
Headings: [('Employee Policy Handbook', 1), ('Introduction', 2), ('Leave Policy', 3), ('Attendance', 5), ...]
```

## Tests

```
python -m pytest
```
