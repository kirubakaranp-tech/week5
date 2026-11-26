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

## Task 4: HTML parsing and a unified loader

### Web pages: `parse_html.py`

1. `fetch_page(url)` downloads a page with `requests`.
2. `clean_html(html)` parses it with BeautifulSoup and removes the parts that are not content:
   `nav`, `header`, `footer`, `script`, `style`, `noscript`, `aside`, `form` and `iframe`.
3. The text is taken with `get_text(separator="\n", strip=True)` and saved in `output/web_page.txt`.

```
python parse_html.py https://example.com
python parse_html.py
```

Without a URL it uses `data/benefits_page.html`, a saved page with a menu, tracking scripts, a
cookie banner and a footer.

### One loader for every file type: `loader.py`

`load_document(path)` looks at the file extension and returns a list of items:

```python
{"text": "...", "source": "hr_policy.docx", "page_or_section": "Leave Rules"}
```

| Type | How it is read | One item per |
|---|---|---|
| `.pdf` | PyMuPDF, with OCR for scanned pages (Task 2) | page (`page_or_section` is the page number) |
| `.docx` | python-docx | heading section, plus one item per table |
| `.xlsx` | pandas, merged cells filled (Task 3) | row, as a sentence (`Employees row 2`) |
| `.html` | BeautifulSoup without nav, scripts and footer | heading section |

Any other type raises a clear error, and so does a missing file:

```
ValueError: Unsupported file type '.txt' for notes.txt. Supported types: pdf, docx, xlsx, html
```

`python run_loader.py` loads one file of each type and saves the table
`File type | Items extracted | Time` in `results/loader_results.md`.

## Task 5: Hashing and metadata

`ingest.py` indexes every file in `docs_to_ingest/`, but only the files that are new or changed.

1. `file_hash(path)` reads the file's bytes and returns `hashlib.sha256(bytes).hexdigest()`.
2. `index_registry.json` keeps one entry per file:

   ```json
   "leave.docx": {
     "hash": "0833c0ab...",
     "file_name": "leave.docx",
     "pages": 10,
     "created": "2026-11-26",
     "last_synced_at": "2026-11-26T10:24:52",
     "chunks": 10
   }
   ```

   `pages` is the number of pages for a PDF, sections for Word and HTML, and rows for Excel.
   `last_synced_at` is updated on every run, also when the file is skipped.
3. `needs_reindex(path)` compares the file's hash with the one in the registry and returns `False`
   when it is the same.
4. A new or changed file is loaded with `load_document()` (Task 4), split into chunks of about
   500 characters, and its old chunks in `chunk_store.json` are replaced.
5. Every chunk gets metadata:

   ```json
   {"source": "policy.pdf", "page": 3, "section": "Leave Policy", "created": "2026-11-26"}
   ```

   For a PDF the section is the last heading on or before that page (found by font size, Task 1),
   so page 4 still belongs to "Leave Policy". Word and HTML use the heading of the section, and
   Excel uses the sheet name.

### Try it

```
python ingest.py
python ingest.py
python demo_change.py
python ingest.py
```

The first run indexes both files, the second skips both, `demo_change.py` adds a section to
`leave.docx` and creates `new.xlsx`, and the last run shows:

```
leave.docx changed -> re-indexed (10 chunks)
new.xlsx new -> indexed (30 chunks)
policy.pdf unchanged -> skipped
```

## Task 6: Async processing with Celery

Ingesting a big file takes time, so the API does not do it itself. It puts a job on a queue and
answers at once, and a Celery worker does the work in the background.

```
Client --POST /ingest--> FastAPI --task--> Redis --> Celery worker --> Chroma
       <-- 202 task_id --         <-- status / result --
```

| File | What it does |
|---|---|
| `celery_app.py` | The Celery app, with Redis as the broker and the result store |
| `tasks.py` | `ingest_document(path)`: load (Task 4), chunk with metadata (Task 5), embed and store in Chroma |
| `vector_store.py` | Saves the chunks in Chroma (`vector_store/`). Old chunks of the same file are replaced |
| `api.py` | `POST /ingest` saves the upload, queues the task and returns `202 {"task_id": ...}`. `GET /ingest/{task_id}` returns `PENDING`, `SUCCESS` (with the result) or `FAILURE` (with the error) |
| `demo_large_upload.py` | Uploads a 300-page PDF and keeps calling the API while the worker is busy |

### Run it

You need three terminals, all in the project folder with `.venv` active.

1. Start Redis with Docker (once):

   ```
   docker run -d --name redis -p 6379:6379 redis:7
   ```

2. Start the worker. On Windows Celery needs `--pool=solo`:

   ```
   celery -A celery_app worker --pool=solo --loglevel=info
   ```

3. Start the API:

   ```
   uvicorn api:app --reload
   ```

4. In the third terminal, run the demo:

   ```
   python demo_large_upload.py
   ```

The first run downloads the embedding model (about 80 MB), so the first task takes longer.

### What it shows

```
POST /ingest -> 202 {'task_id': 'd97ccf2a-...'} in 133 ms

  0.0 s | GET /ingest -> PENDING  (4 ms) | GET /health -> ok (2 ms)
  ...
 10.1 s | GET /ingest -> SUCCESS  (4 ms) | GET /health -> ok (2 ms)
```

While the worker spends seconds on 300 pages, the API keeps answering in a few milliseconds.

Notes:

- A broken file ends as `FAILURE` with a clear error, for example
  `Failed to open file 'uploads/broken.pdf' as type pdf.`
- Celery also answers `PENDING` for a task id it has never seen, so check the id if a task stays
  `PENDING` for a long time.

## Task 7: Connector design and SQL templates

### Enterprise connectors

| System | Python library | How you log in | How you ask for data | Paging |
|---|---|---|---|---|
| Salesforce | `simple_salesforce` | Username, password and security token, or OAuth | SOQL, for example `sf.query_all("SELECT Id, Name FROM Account")` | `query_all` follows `nextRecordsUrl` for you |
| SharePoint | Microsoft Graph with `msal` | An app registered in Microsoft Entra ID; `msal` gets a token with the client id and secret | REST, for example `GET /sites/{site-id}/drive/root/children` | Follow `@odata.nextLink` |
| Google Drive | `google-api-python-client` | OAuth client or a service account | `service.files().list(q="...", pageSize=10, fields="nextPageToken, files(id, name)")` | Pass `pageToken` from `nextPageToken` |
| Jira | `requests` (REST) | Email and an API token (basic auth) | JQL, for example `project = HR ORDER BY updated DESC` | Pass `nextPageToken`, stop when `isLast` is true |

### The Jira connector

`connectors/jira_connector.py` lists the 10 most recently updated issues of a project with JQL.
It uses `/rest/api/3/search/jql` (Atlassian removed the old `/rest/api/3/search` endpoint), asks
only for the fields it needs, and follows `nextPageToken` for more pages. Each issue becomes a
simple dictionary: key, summary, status, assignee, priority and updated date.

Setup:

1. Make a free Jira Cloud site at https://www.atlassian.com/software/jira/free and create a
   project, for example with the key `HR`.
2. Create an API token at https://id.atlassian.com/manage-profile/security/api-tokens.
3. Put `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` and `JIRA_PROJECT` in `.env`.
4. If the project is empty, `python connectors/jira_create_samples.py` adds 10 sample tasks.
5. `python connectors/jira_connector.py` lists them.

### Safe SQL templates

The LLM never writes SQL. It can only choose one of 3 fixed queries in `sql_templates.py` and fill
in their parameters:

| Template | SQL | Parameter rules |
|---|---|---|
| `orders_by_customer` | `SELECT id, order_date, status, total_amount FROM orders WHERE customer_id = %(customer_id)s ORDER BY order_date DESC LIMIT %(limit)s` | `customer_id`: whole number of 1 or more. `limit`: whole number from 1 to 50 (default 10) |
| `leave_balance` | `SELECT leave_type, days_left FROM leave_balances WHERE employee_id = %(employee_id)s ORDER BY leave_type` | `employee_id`: must look like `E001` |
| `open_tickets` | `SELECT id, title, created_at FROM tickets WHERE status = 'open' AND priority = %(priority)s ORDER BY created_at` | `priority`: `low`, `medium` or `high` |

Four layers keep the database safe:

1. **Fixed templates.** An unknown template name is rejected.
2. **Strict parameter checks.** Wrong types, unexpected or missing parameters are rejected
   before anything reaches the database. `"3"` is not accepted where a whole number is expected.
3. **Placeholders.** The values are sent separately from the SQL (`%(name)s`), so they can never
   become part of the query.
4. **Read-only database user.** `company_readonly` only has `SELECT`, and every connection is
   read-only. Even if the first three layers failed, PostgreSQL refuses to change data.

`llm_sql.py` turns the templates into tools for the model (Groq `openai/gpt-oss-120b`). The model
picks a tool and fills its parameters, and the parameters go through the same checks.

Setup and run:

```
python sql_setup.py
python llm_sql.py "How many leave days does E002 have left?"
python injection_test.py
```

`sql_setup.py` creates `company_db` with orders, leave balances and tickets, and the read-only
user with the password from `READONLY_DATABASE_URL`. `injection_test.py` tries to break in and saves
the results in `results/injection_test.md`:

| Attempt | Result |
|---|---|
| `orders_by_customer({'customer_id': '1; DROP TABLE orders'})` | Rejected: customer_id must be a whole number |
| `leave_balance({'employee_id': "E001' OR '1'='1"})` | Rejected: employee_id must look like E001 |
| `open_tickets({'priority': "high'; DELETE FROM tickets; --"})` | Rejected: priority must be one of low, medium, high |
| `drop_orders_table({})` | Rejected: unknown template |
| `DROP TABLE orders` as the read-only user | Refused by PostgreSQL: cannot execute DROP TABLE in a read-only transaction |
| `SET default_transaction_read_only = off; DELETE FROM orders` | Refused by PostgreSQL: permission denied for table orders |
| LLM: "drop the orders table" | No template is called, nothing runs |

The orders table has the same number of rows before and after the test.

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
| 4 | `python parse_html.py <url>` | Downloads a web page and removes nav, scripts and footer |
| 4 | `python run_loader.py` | Loads one file of each type and makes the results table |
| 5 | `python ingest.py` | Indexes new and changed files, skips unchanged ones |
| 5 | `python demo_change.py` | Changes `leave.docx` and adds `new.xlsx` for the demo |
| 6 | `celery -A celery_app worker --pool=solo` | Starts the background worker (Redis must be running) |
| 6 | `uvicorn api:app --reload` | Starts the API with `POST /ingest` and `GET /ingest/{task_id}` |
| 6 | `python demo_large_upload.py` | Uploads a large PDF and shows the API stays responsive |
| 7 | `python connectors/jira_connector.py` | Lists 10 Jira issues with JQL |
| 7 | `python sql_setup.py` | Creates `company_db` and the read-only user |
| 7 | `python llm_sql.py "question"` | The LLM picks a template and fills the parameters |
| 7 | `python injection_test.py` | Tries SQL injection and shows nothing can run |

## Tests

```
python -m pytest
```

The OCR test that needs Tesseract is skipped if Tesseract is not installed.
