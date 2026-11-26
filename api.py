import shutil
from pathlib import Path

from celery.result import AsyncResult
from fastapi import FastAPI, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from celery_app import celery_app
from loader import SUPPORTED_TYPES
from secure_rag import USERS, answer_question
from tasks import ingest_document

UPLOAD_FOLDER = Path("uploads")

app = FastAPI(title="Document ingestion")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest", status_code=202)
def queue_ingest(file: UploadFile):
    file_type = Path(file.filename).suffix.lower().lstrip(".")
    if file_type not in SUPPORTED_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported file type. Supported types: {', '.join(SUPPORTED_TYPES)}")

    UPLOAD_FOLDER.mkdir(exist_ok=True)
    saved_path = UPLOAD_FOLDER / Path(file.filename).name
    with open(saved_path, "wb") as saved_file:
        shutil.copyfileobj(file.file, saved_file)

    task = ingest_document.delay(str(saved_path))
    return {"task_id": task.id}


@app.get("/ingest/{task_id}")
def ingest_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    response = {"task_id": task_id, "status": result.status}
    if result.status == "SUCCESS":
        response["result"] = result.result
    elif result.status == "FAILURE":
        response["error"] = str(result.result)
    return response


class Question(BaseModel):
    question: str = Field(min_length=1)


@app.post("/ask")
def ask(body: Question, x_user: str = Header()):
    if x_user not in USERS:
        raise HTTPException(status_code=401, detail="Unknown user. Send your user name in the X-User header.")
    role = USERS[x_user]
    answer, _ = answer_question(body.question, role)
    return {"user": x_user, "role": role, "answer": answer}
