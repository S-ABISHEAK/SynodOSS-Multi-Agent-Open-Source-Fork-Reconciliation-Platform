from celery import Celery
from src.core.config import settings

celery_app = Celery(
    "synodoss_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["src.workers.tasks"]
)
