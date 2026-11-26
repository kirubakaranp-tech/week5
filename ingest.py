import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pymupdf as fitz

from extract_pdf import find_headings, get_body_font_size
from loader import SUPPORTED_TYPES, load_document

DEFAULT_FOLDER = Path("docs_to_ingest")
REGISTRY_FILE = Path("index_registry.json")
CHUNK_STORE_FILE = Path("chunk_store.json")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def file_hash(path):
    data = Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest()


def load_json(path):
    if Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return {}


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_status(path, registry):
    entry = registry.get(Path(path).name)
    if entry is None:
        return "new"
    if entry["hash"] != file_hash(path):
        return "changed"
    return "unchanged"


def needs_reindex(path, registry=None):
    if registry is None:
        registry = load_json(REGISTRY_FILE)
    return get_status(path, registry) != "unchanged"


def split_into_chunks(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()
    chunks = []
    current = []
    for word in words:
        if current and len(" ".join(current + [word])) > size:
            chunks.append(" ".join(current))
            kept = []
            for previous in reversed(current):
                if len(" ".join([previous] + kept)) > overlap:
                    break
                kept.insert(0, previous)
            current = kept
        current.append(word)
    if current:
        chunks.append(" ".join(current))
    return chunks


def pdf_headings_by_page(path):
    headings = {}
    with fitz.open(path) as doc:
        body_size = get_body_font_size(doc)
        current = None
        for page in doc:
            found = find_headings(page, body_size)
            if found:
                current = found[0]
            headings[page.number + 1] = current
    return headings


def make_chunks(path, created):
    path = Path(path)
    items = load_document(path)
    pdf_headings = pdf_headings_by_page(path) if path.suffix.lower() == ".pdf" else {}

    chunks = []
    for item in items:
        place = item["page_or_section"]
        if isinstance(place, int):
            page = place
            section = pdf_headings.get(place)
        else:
            page = None
            section = place.split(" row ")[0]

        for text in split_into_chunks(item["text"]):
            chunks.append({
                "id": f"{path.name}-{len(chunks)}",
                "text": text,
                "metadata": {"source": path.name, "page": page, "section": section, "created": created},
            })
    return chunks, len(items)


def ingest_folder(folder=DEFAULT_FOLDER):
    registry = load_json(REGISTRY_FILE)
    store = load_json(CHUNK_STORE_FILE)
    now = datetime.now().isoformat(timespec="seconds")

    for path in sorted(Path(folder).iterdir()):
        if path.suffix.lower().lstrip(".") not in SUPPORTED_TYPES:
            continue

        status = get_status(path, registry)
        if status == "unchanged":
            registry[path.name]["last_synced_at"] = now
            print(f"{path.name} unchanged -> skipped")
            continue

        created = datetime.fromtimestamp(path.stat().st_ctime).strftime("%Y-%m-%d")
        chunks, pages = make_chunks(path, created)
        store[path.name] = chunks
        registry[path.name] = {
            "hash": file_hash(path),
            "file_name": path.name,
            "pages": pages,
            "created": created,
            "last_synced_at": now,
            "chunks": len(chunks),
        }
        action = "re-indexed" if status == "changed" else "indexed"
        print(f"{path.name} {status} -> {action} ({len(chunks)} chunks)")

    save_json(REGISTRY_FILE, registry)
    save_json(CHUNK_STORE_FILE, store)
    return registry


if __name__ == "__main__":
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FOLDER
    ingest_folder(folder)
    print(f"\nRegistry saved in {REGISTRY_FILE}, chunks saved in {CHUNK_STORE_FILE}")
