import time
from datetime import datetime
from pathlib import Path

from celery_app import celery_app
from ingest import make_chunks
from vector_store import store_chunks


@celery_app.task(name="ingest_document")
def ingest_document(path):
    start = time.perf_counter()
    path = Path(path)
    created = datetime.fromtimestamp(path.stat().st_ctime).strftime("%Y-%m-%d")

    chunks, pages = make_chunks(path, created)
    total_in_store = store_chunks(path.name, chunks)

    return {
        "file": path.name,
        "pages": pages,
        "chunks": len(chunks),
        "chunks_in_store": total_in_store,
        "seconds": round(time.perf_counter() - start, 1),
    }
