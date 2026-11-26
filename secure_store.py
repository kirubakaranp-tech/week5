import json
from datetime import datetime
from pathlib import Path

import chromadb

import vector_store
from ingest import file_hash, get_status, load_json, make_chunks, save_json
from loader import SUPPORTED_TYPES

SECURE_FOLDER = Path("secure_docs")
ACCESS_RULES_FILE = SECURE_FOLDER / "access_rules.json"
REGISTRY_FILE = Path("secure_registry.json")
COLLECTION_NAME = "secure_documents"


def get_collection():
    client = chromadb.PersistentClient(path=str(vector_store.CHROMA_FOLDER))
    return client.get_or_create_collection(COLLECTION_NAME, embedding_function=vector_store.embedding_function)


def get_allowed_roles(file_name):
    rules = json.loads(ACCESS_RULES_FILE.read_text(encoding="utf-8"))
    return rules.get(file_name, "all")


def store_document(path):
    path = Path(path)
    created = datetime.fromtimestamp(path.stat().st_ctime).strftime("%Y-%m-%d")
    chunks, pages = make_chunks(path, created)
    allowed_roles = get_allowed_roles(path.name)

    collection = get_collection()
    collection.delete(where={"source": path.name})
    if chunks:
        metadatas = []
        for chunk in chunks:
            metadata = {key: value for key, value in chunk["metadata"].items() if value is not None}
            metadata["allowed_roles"] = allowed_roles
            metadatas.append(metadata)
        collection.add(
            ids=[chunk["id"] for chunk in chunks],
            documents=[chunk["text"] for chunk in chunks],
            metadatas=metadatas,
        )
    return len(chunks), pages, allowed_roles


def sync_document(path, registry, now):
    path = Path(path)
    status = get_status(path, registry)

    if status == "unchanged":
        registry[path.name]["last_synced_at"] = now
        return "unchanged"

    chunk_count, pages, allowed_roles = store_document(path)
    registry[path.name] = {
        "hash": file_hash(path),
        "file_name": path.name,
        "pages": pages,
        "allowed_roles": allowed_roles,
        "chunks": chunk_count,
        "last_synced_at": now,
    }
    return status


def sync_folder(folder=SECURE_FOLDER):
    registry = load_json(REGISTRY_FILE)
    now = datetime.now().isoformat(timespec="seconds")

    for path in sorted(Path(folder).iterdir()):
        if path.suffix.lower().lstrip(".") in SUPPORTED_TYPES:
            status = sync_document(path, registry, now)
            entry = registry[path.name]
            print(f"{path.name}: {status} | allowed_roles={entry['allowed_roles']} | {entry['chunks']} chunks")

    save_json(REGISTRY_FILE, registry)
    return registry


if __name__ == "__main__":
    sync_folder()
    print(f"\nRegistry saved in {REGISTRY_FILE}")
