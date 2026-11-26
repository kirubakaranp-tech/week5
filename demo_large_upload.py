import time
from pathlib import Path

import pymupdf as fitz
import requests

API_URL = "http://127.0.0.1:8000"
LARGE_FILE = Path("data") / "large_policy.pdf"
COPIES = 25


def make_large_pdf():
    if LARGE_FILE.exists():
        return
    source = fitz.open("data/employee_policy.pdf")
    large = fitz.open()
    for _ in range(COPIES):
        large.insert_pdf(source)
    large.save(LARGE_FILE)
    print(f"Created {LARGE_FILE} with {large.page_count} pages")


def timed_get(url):
    start = time.perf_counter()
    response = requests.get(url, timeout=10)
    return response.json(), (time.perf_counter() - start) * 1000


def main():
    make_large_pdf()

    start = time.perf_counter()
    with open(LARGE_FILE, "rb") as file:
        response = requests.post(f"{API_URL}/ingest", files={"file": (LARGE_FILE.name, file)}, timeout=60)
    upload_ms = (time.perf_counter() - start) * 1000
    task_id = response.json()["task_id"]
    print(f"POST /ingest -> {response.status_code} {response.json()} in {upload_ms:.0f} ms\n")

    started = time.perf_counter()
    while True:
        status, status_ms = timed_get(f"{API_URL}/ingest/{task_id}")
        health, health_ms = timed_get(f"{API_URL}/health")
        seconds = time.perf_counter() - started
        print(f"{seconds:5.1f} s | GET /ingest -> {status['status']:8} ({status_ms:.0f} ms) "
              f"| GET /health -> {health['status']} ({health_ms:.0f} ms)")

        if status["status"] in ("SUCCESS", "FAILURE"):
            print(f"\nFinal answer: {status}")
            break
        time.sleep(1)


if __name__ == "__main__":
    main()
