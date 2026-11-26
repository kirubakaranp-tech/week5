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

## Task 2: Scanned PDF and OCR

`data/policy_mixed.pdf` has 4 pages: pages 1 and 2 are normal digital pages, pages 3 and 4 are
scans (images only, slightly tilted, with noise and blur like a real scanner).

`ocr_pdf.py` has `extract_text(pdf, lang="eng")`:

1. It first reads each page normally with PyMuPDF.
2. If a page has fewer than 20 characters, it is treated as a scan: pdf2image turns the page into
   an image at 300 DPI and `pytesseract.image_to_string` reads it.
3. Every page is returned with the method used (`normal` or `ocr`) and the time it took.

`compare_ocr.py` compares page 3 of the original digital PDF with the OCR text of the same page
in the scanned PDF. It counts how many of the original words OCR found (word match) and lists the
words it missed. Both texts are saved side by side in `results/ocr_comparison.md`.

### Why OCR fails and how to improve it

| Problem | What happens | How to improve |
|---|---|---|
| Low resolution | Small letters lose detail, so `rn` becomes `m` and `l` becomes `1` | Scan or convert at 300 DPI or more (`dpi=300` in pdf2image) |
| Tilted page (skew) | Lines are not straight, so words are split or joined | Deskew the image first, for example with Tesseract's orientation detection (`pytesseract.image_to_osd`) or OpenCV, and scan pages straight |
| Wrong language | Tesseract only knows the letters of the languages it is told, so Tamil text becomes nonsense with `lang="eng"` | Install the language data and pass it, for example `lang="eng+tam"` |
| Tables and lines | Grid lines are read as letters like `\|` or `'`, and words in cells get joined | Remove lines before OCR, or try another page mode like `config="--psm 6"` |
| Noise and low contrast | Dots and grey background are read as characters | Convert to black and white (thresholding) and remove noise before OCR |

### Bonus: Tamil and English

`data/tamil_english.pdf` is a scanned page with the leave policy in English and Tamil.

```
python ocr_pdf.py data/tamil_english.pdf eng
python ocr_pdf.py data/tamil_english.pdf eng+tam
```

With `eng` only, the Tamil lines come out as random Latin characters. With `eng+tam`, both
languages are read.

## Task 3: DOCX and Excel parsing

### Word: `parse_docx.py`

The input is `data/hr_policy.docx`, an HR policy summary with 8 headings and 2 tables.

1. Prints every paragraph with its style, for example `[Heading 1] Leave Rules`.
2. Reads every table cell with `table.cell(r, c).text`.
3. Turns each table into a list of dictionaries, using the first row as the keys, and saves them in
   `output/docx_tables.json`.

### Excel: `parse_excel.py`

The input is `data/hr_data.xlsx` with two sheets, Employees and Leaves.

1. Reads all sheets with `pandas.read_excel(path, sheet_name=None)` and prints each sheet's name
   and shape.
2. Turns every row into a sentence for RAG, for example `Employee Arun in Sales earns 30000` or
   `Employee E019 took 1 day of Sick leave from 2026-09-10`, and saves them in
   `output/excel_sentences.txt`.

### Empty and merged cells

| Case | What happens | How it is handled |
|---|---|---|
| Merged cell in Word | `table.cell(r, c)` returns the same cell for every position it covers | The text is kept for every row it covers, and merged cells are counted |
| Merged cell in Excel | pandas only gives the value to the first cell, the others are empty (NaN) | The Department column is filled from the cell above with `ffill()` |
| Empty cell in Word | The text is `""` | Saved as `None` |
| Empty cell in Excel | The value is NaN, and whole numbers turn into floats like `30000.0` | NaN becomes `None`, `30000.0` becomes `30000`, and the sentence says so, for example `has no salary recorded` |
| Empty or repeated header | Two columns would get the same key | They get names like `Column 2` or `Name 3` |

## Setup

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Task 2 also needs two programs on Windows:

1. **Tesseract OCR**: install it from https://github.com/UB-Mannheim/tesseract/wiki. During the
   install, open "Additional language data" and tick **Tamil** for the bonus.
2. **Poppler** (used by pdf2image): download the latest zip from
   https://github.com/oschwartz10612/poppler-windows/releases and unzip it to `C:\poppler`.

Then copy `.env.example` to `.env` and check the two paths in it.

## Run

| Task | Command | What it does |
|---|---|---|
| 1 | `python extract_pdf.py` | Text, layout blocks, headings and one JSON per page |
| 2 | `python ocr_pdf.py` | Reads the mixed PDF, with OCR only for the scanned pages |
| 2 | `python compare_ocr.py` | Compares normal extraction and OCR on page 3 |
| Bonus | `python ocr_pdf.py data/tamil_english.pdf eng+tam` | OCR of a Tamil and English page |
| 3 | `python parse_docx.py` | Paragraphs with styles and tables as dictionaries |
| 3 | `python parse_excel.py` | Sheet names, shapes and one sentence per row |

## Tests

```
python -m pytest
```

The OCR test that needs Tesseract is skipped if Tesseract is not installed.
