from celery import Celery

from .core.config import settings

celery_app = Celery(
    "evently",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"]
)

celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
    worker_send_task_events=True,
    worker_prefetch_multiplier=1,
)