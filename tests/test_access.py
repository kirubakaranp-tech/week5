import json
import re
import shutil
from datetime import datetime, timedelta

import chromadb
import pytest
from fastapi.testclient import TestClient

import api
import freshness
import secure_rag
import secure_store
import tasks
import vector_store
from celery_app import celery_app

QUESTION = "What is the salary revision cycle and how much increase does a rating of 4 get?"
KEYWORDS = ["salary", "revision", "rating", "increase", "leave", "sick", "bonus", "insurance", "learning", "payroll"]


class KeywordEmbedding(chromadb.EmbeddingFunction):
    def __init__(self):
        pass

    def __call__(self, input):
        vectors = []
        for text in input:
            vector = [float(text.lower().count(word)) for word in KEYWORDS] + [0.1]
            length = sum(value * value for value in vector) ** 0.5
            vectors.append([value / length for value in vector])
        return vectors

    @staticmethod
    def name():
        return "keywords"

    def get_config(self):
        return {}

    @staticmethod
    def build_from_config(config):
        return KeywordEmbedding()


def fake_ask(prompt):
    for number, text in re.findall(r"\[(\d+)\] (.*?)(?=\n\n\[\d+\]|\n\nQuestion:)", prompt, re.S):
        if "salary revision cycle is annual" in text:
            return f"The salary revision cycle is annual and a rating of 4 gets 9%. [{number}]"
    return "I don't know."


@pytest.fixture
def secure_folder(tmp_path, monkeypatch):
    folder = tmp_path / "secure_docs"
    shutil.copytree("secure_docs", folder)
    monkeypatch.setattr(vector_store, "CHROMA_FOLDER", tmp_path / "chroma")
    monkeypatch.setattr(vector_store, "embedding_function", KeywordEmbedding())
    monkeypatch.setattr(secure_store, "SECURE_FOLDER", folder)
    monkeypatch.setattr(secure_store, "ACCESS_RULES_FILE", folder / "access_rules.json")
    monkeypatch.setattr(secure_store, "REGISTRY_FILE", tmp_path / "secure_registry.json")
    monkeypatch.setattr(freshness, "REGISTRY_FILE", tmp_path / "secure_registry.json")
    monkeypatch.setattr(freshness, "SECURE_FOLDER", folder)
    monkeypatch.setattr(secure_rag, "ask", fake_ask)
    secure_store.sync_folder(folder)
    return folder


def test_every_chunk_has_allowed_roles(secure_folder):
    stored = secure_store.get_collection().get(include=["metadatas"])
    roles = {metadata["source"]: metadata["allowed_roles"] for metadata in stored["metadatas"]}
    assert roles == {"hr_policy.pdf": "hr", "leave_policy.docx": "all", "benefits_page.html": "all"}


@pytest.mark.parametrize("question", [QUESTION, "bonus payroll salary", "What is the target bonus?"])
def test_employee_never_gets_hr_chunks(secure_folder, question):
    chunks = secure_rag.retrieve(question, "employee")
    assert chunks
    assert all(chunk["allowed_roles"] == "all" for chunk in chunks)


def test_hr_gets_hr_chunks(secure_folder):
    chunks = secure_rag.retrieve(QUESTION, "hr")
    assert any(chunk["source"] == "hr_policy.pdf" and chunk["page"] == 4 for chunk in chunks)


def test_unknown_role_is_refused(secure_folder):
    with pytest.raises(ValueError, match="Unknown role"):
        secure_rag.retrieve(QUESTION, "intern")


def test_employee_gets_i_dont_know_and_hr_gets_the_answer(secure_folder):
    employee_answer, _ = secure_rag.answer_question(QUESTION, "employee")
    hr_answer, _ = secure_rag.answer_question(QUESTION, "hr")
    assert employee_answer == "I don't know."
    assert hr_answer.startswith("The salary revision cycle is annual")
    assert hr_answer.endswith("(Source: hr_policy.pdf p.4)")


def test_ask_endpoint_uses_the_logged_in_user(secure_folder):
    client = TestClient(api.app)
    employee = client.post("/ask", json={"question": QUESTION}, headers={"X-User": "arun"}).json()
    hr = client.post("/ask", json={"question": QUESTION}, headers={"X-User": "meena"}).json()

    assert employee == {"user": "arun", "role": "employee", "answer": "I don't know."}
    assert hr["role"] == "hr"
    assert "hr_policy.pdf p.4" in hr["answer"]
    assert client.post("/ask", json={"question": QUESTION}, headers={"X-User": "stranger"}).status_code == 401
    assert client.post("/ask", json={"question": QUESTION}).status_code == 422


def set_last_synced(file_name, hours_ago):
    registry = json.loads(secure_store.REGISTRY_FILE.read_text(encoding="utf-8"))
    registry[file_name]["last_synced_at"] = (datetime.now() - timedelta(hours=hours_ago)).isoformat(timespec="seconds")
    secure_store.REGISTRY_FILE.write_text(json.dumps(registry), encoding="utf-8")


def test_only_documents_older_than_24_hours_are_refreshed(secure_folder):
    set_last_synced("leave_policy.docx", 30)
    set_last_synced("benefits_page.html", 23)

    assert freshness.refresh_stale_documents() == ["leave_policy.docx"]

    registry = json.loads(secure_store.REGISTRY_FILE.read_text(encoding="utf-8"))
    assert freshness.hours_since(registry["leave_policy.docx"]["last_synced_at"], datetime.now()) < 1


def test_changed_stale_document_is_reindexed(secure_folder, capsys):
    page = secure_folder / "benefits_page.html"
    page.write_text(page.read_text(encoding="utf-8").replace("Rs 40,000", "Rs 50,000"), encoding="utf-8")
    set_last_synced("benefits_page.html", 48)

    freshness.refresh_stale_documents()

    assert "benefits_page.html: synced 48.0 h ago -> re-synced (re-indexed)" in capsys.readouterr().out
    texts = secure_store.get_collection().get(where={"source": "benefits_page.html"})["documents"]
    assert any("Rs 50,000" in text for text in texts)


def test_deleted_document_leaves_the_registry(secure_folder):
    (secure_folder / "benefits_page.html").unlink()
    set_last_synced("benefits_page.html", 48)
    freshness.refresh_stale_documents()
    registry = json.loads(secure_store.REGISTRY_FILE.read_text(encoding="utf-8"))
    assert "benefits_page.html" not in registry
    assert secure_store.get_collection().get(where={"source": "benefits_page.html"})["ids"] == []


def test_celery_beat_runs_the_refresh_every_hour():
    schedule = celery_app.conf.beat_schedule["refresh-stale-documents-every-hour"]
    assert schedule == {"task": "refresh_stale_documents", "schedule": 3600.0}
    assert "refresh_stale_documents" in celery_app.tasks
    assert tasks.refresh_stale.name == "refresh_stale_documents"
