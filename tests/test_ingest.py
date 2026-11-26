import hashlib
import shutil

import pytest

import demo_change
import ingest
from ingest import (
    file_hash,
    get_status,
    ingest_folder,
    needs_reindex,
    split_into_chunks,
)


@pytest.fixture
def folder(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "REGISTRY_FILE", tmp_path / "index_registry.json")
    monkeypatch.setattr(ingest, "CHUNK_STORE_FILE", tmp_path / "chunk_store.json")
    documents = tmp_path / "docs"
    documents.mkdir()
    shutil.copy("docs_to_ingest/policy.pdf", documents)
    shutil.copy("docs_to_ingest/leave.docx", documents)
    return documents


def test_file_hash_is_sha256_of_the_bytes(tmp_path):
    path = tmp_path / "a.txt"
    path.write_bytes(b"hello")
    assert file_hash(path) == hashlib.sha256(b"hello").hexdigest()


def test_split_into_chunks_keeps_size_and_overlap():
    text = " ".join(f"word{number}" for number in range(300))
    chunks = split_into_chunks(text, size=100, overlap=20)
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert chunks[0].split()[-1] in chunks[1]


def test_first_run_indexes_everything(folder, capsys):
    registry = ingest_folder(folder)

    assert set(registry) == {"leave.docx", "policy.pdf"}
    entry = registry["policy.pdf"]
    assert entry["hash"] == file_hash(folder / "policy.pdf")
    assert entry["pages"] == 12
    assert set(entry) == {"hash", "file_name", "pages", "created", "last_synced_at", "chunks"}
    assert "policy.pdf new -> indexed" in capsys.readouterr().out


def test_unchanged_file_is_skipped(folder, capsys):
    ingest_folder(folder)
    assert needs_reindex(folder / "policy.pdf", ingest.load_json(ingest.REGISTRY_FILE)) is False

    ingest_folder(folder)
    output = capsys.readouterr().out
    assert "policy.pdf unchanged -> skipped" in output
    assert "leave.docx unchanged -> skipped" in output


def test_only_the_changed_file_is_reindexed(folder, capsys, monkeypatch):
    ingest_folder(folder)
    store_before = ingest.load_json(ingest.CHUNK_STORE_FILE)

    monkeypatch.setattr(demo_change, "FOLDER", folder)
    demo_change.change_leave_docx()
    demo_change.create_new_xlsx()
    registry = ingest.load_json(ingest.REGISTRY_FILE)
    assert get_status(folder / "leave.docx", registry) == "changed"
    assert get_status(folder / "new.xlsx", registry) == "new"
    assert get_status(folder / "policy.pdf", registry) == "unchanged"

    capsys.readouterr()
    ingest_folder(folder)
    output = capsys.readouterr().out
    assert "policy.pdf unchanged -> skipped" in output
    assert "leave.docx changed -> re-indexed" in output
    assert "new.xlsx new -> indexed (30 chunks)" in output

    store_after = ingest.load_json(ingest.CHUNK_STORE_FILE)
    assert store_after["policy.pdf"] == store_before["policy.pdf"]
    assert len(store_after["leave.docx"]) == len(store_before["leave.docx"]) + 1


def test_every_chunk_has_metadata(folder):
    ingest_folder(folder)
    store = ingest.load_json(ingest.CHUNK_STORE_FILE)

    for chunks in store.values():
        for chunk in chunks:
            assert set(chunk["metadata"]) == {"source", "page", "section", "created"}

    page_four = [chunk for chunk in store["policy.pdf"] if chunk["metadata"]["page"] == 4]
    assert page_four[0]["metadata"]["section"] == "Leave Policy"
    sick = [chunk for chunk in store["leave.docx"] if chunk["metadata"]["section"] == "Sick Leave"]
    assert "medical certificate" in sick[0]["text"]
