import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DEFAULT_FILE = Path("data") / "benefits_page.html"
OUTPUT_FILE = Path("output") / "web_page.txt"
BOILERPLATE_TAGS = ["nav", "header", "footer", "script", "style", "noscript", "aside", "form", "iframe"]


def fetch_page(url):
    response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (enterprise-docs learning project)"})
    response.raise_for_status()
    return response.text


def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(BOILERPLATE_TAGS):
        tag.decompose()
    return soup


def html_to_text(html):
    return clean_html(html).get_text(separator="\n", strip=True)


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_FILE)

    if source.startswith("http://") or source.startswith("https://"):
        html = fetch_page(source)
    else:
        html = Path(source).read_text(encoding="utf-8")

    raw_text = BeautifulSoup(html, "html.parser").get_text(separator="\n", strip=True)
    clean_text = html_to_text(html)

    print(f"Source: {source}")
    print(f"Before cleaning: {len(raw_text)} characters")
    print(f"After removing nav, scripts and footer: {len(clean_text)} characters")
    print("\nFirst lines of the clean text:")
    for line in clean_text.splitlines()[:8]:
        print(f"  {line}")

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(clean_text, encoding="utf-8")
    print(f"\nSaved the clean text in {OUTPUT_FILE}")
