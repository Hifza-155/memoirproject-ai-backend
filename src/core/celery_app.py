from celery import Celery

from src.core.config import settings

celery_app = Celery(
    "memoir",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.domain.transcription_tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=600,
    task_soft_time_limit=540,
)