from types import SimpleNamespace

import chromadb
import pytest
from fastapi.testclient import TestClient

import api
import vector_store
from tasks import ingest_document

client = TestClient(api.app)


class FakeEmbedding(chromadb.EmbeddingFunction):
    def __init__(self):
        pass

    def __call__(self, input):
        return [[float(len(text) % 7), float(text.count("leave")), 1.0] for text in input]

    @staticmethod
    def name():
        return "fake"

    def get_config(self):
        return {}

    @staticmethod
    def build_from_config(config):
        return FakeEmbedding()


@pytest.fixture
def fake_store(tmp_path, monkeypatch):
    monkeypatch.setattr(vector_store, "CHROMA_FOLDER", tmp_path / "chroma")
    monkeypatch.setattr(vector_store, "embedding_function", FakeEmbedding())


def test_task_loads_chunks_embeds_and_stores(fake_store):
    result = ingest_document("docs_to_ingest/policy.pdf")

    assert result["file"] == "policy.pdf"
    assert result["pages"] == 12
    assert result["chunks"] == result["chunks_in_store"] > 12

    stored = vector_store.get_collection().get(include=["metadatas"])
    assert {metadata["source"] for metadata in stored["metadatas"]} == {"policy.pdf"}
    assert "section" in stored["metadatas"][0]


def test_running_the_task_twice_replaces_the_old_chunks(fake_store):
    first = ingest_document("docs_to_ingest/leave.docx")
    second = ingest_document("docs_to_ingest/leave.docx")
    assert second["chunks_in_store"] == first["chunks_in_store"]


def test_post_ingest_queues_the_task_and_returns_202(tmp_path, monkeypatch):
    queued = []
    monkeypatch.setattr(api, "UPLOAD_FOLDER", tmp_path / "uploads")
    monkeypatch.setattr(api.ingest_document, "delay", lambda path: queued.append(path) or SimpleNamespace(id="abc"))

    with open("docs_to_ingest/policy.pdf", "rb") as file:
        response = client.post("/ingest", files={"file": ("policy.pdf", file)})

    assert response.status_code == 202
    assert response.json() == {"task_id": "abc"}
    assert queued == [str(tmp_path / "uploads" / "policy.pdf")]
    assert (tmp_path / "uploads" / "policy.pdf").exists()


def test_post_ingest_rejects_unsupported_files():
    response = client.post("/ingest", files={"file": ("notes.txt", b"hello")})
    assert response.status_code == 415


@pytest.mark.parametrize(
    "status, result, expected",
    [
        ("PENDING", None, {"task_id": "abc", "status": "PENDING"}),
        ("SUCCESS", {"file": "policy.pdf", "chunks": 26}, {"task_id": "abc", "status": "SUCCESS", "result": {"file": "policy.pdf", "chunks": 26}}),
        ("FAILURE", ValueError("broken file"), {"task_id": "abc", "status": "FAILURE", "error": "broken file"}),
    ],
)
def test_get_ingest_status(monkeypatch, status, result, expected):
    monkeypatch.setattr(api, "AsyncResult", lambda task_id, app: SimpleNamespace(status=status, result=result))
    assert client.get("/ingest/abc").json() == expected


def test_health():
    assert client.get("/health").json() == {"status": "ok"}
