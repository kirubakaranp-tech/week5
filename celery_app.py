import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("enterprise_docs", broker=REDIS_URL, backend=REDIS_URL, include=["tasks"])
celery_app.conf.result_expires = 3600
