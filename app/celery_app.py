from __future__ import annotations

import logging
from typing import Any

from celery import Celery, Task
from celery.signals import setup_logging
from kombu import Queue

from .core.config import settings

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Celery App
# -----------------------------------------------------------------------------
celery_app = Celery(
    "evently",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=settings.CELERY_ENABLE_UTC,
    task_routes={
        "app.tasks.send_booking_confirmation_email": {"queue": "emails"},
        "app.tasks.send_event_reminder_emails": {"queue": "reminders"},
        "app.tasks.notify_waitlist_users": {"queue": "notifications"},
        "app.tasks.schedule_event_reminders": {"queue": "scheduled"},
    },
    task_default_queue="default",
    task_queues={
        "default": Queue("default"),
        "emails": Queue("emails"),
        "reminders": Queue("reminders"),
        "notifications": Queue("notifications"),
        "scheduled": Queue("scheduled"),
    },
    worker_send_task_events=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    task_acks_late=True,
    task_track_started=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    result_expires=3600,
    result_compression="gzip",
    task_soft_time_limit=300,
    task_time_limit=600,
    task_default_retry_delay=60,
    task_max_retries=3,
    task_annotations={
        "app.tasks.send_booking_confirmation_email": {"rate_limit": "100/m"},
        "app.tasks.send_event_reminder_emails": {"rate_limit": "50/m"},
        "app.tasks.notify_waitlist_users": {"rate_limit": "30/m"},
    },
)

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------


@setup_logging.connect  # type: ignore[misc]
def config_loggers(*args: Any, **kwargs: Any) -> None:
    """Configure logging for Celery workers."""
    from logging.config import dictConfig

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "level": "INFO",
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
            },
            "root": {"level": "INFO", "handlers": ["console"]},
            "loggers": {
                "celery": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False,
                },
                "app.tasks": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False,
                },
            },
        }
    )


# -----------------------------------------------------------------------------
# Custom Base Task
# -----------------------------------------------------------------------------


class CallbackTask(Task):
    """Base task class with structured logging for lifecycle events."""

    abstract = True  # ensures this is only used as a base class

    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,  # Celery passes an ExceptionInfo, no stubs available
    ) -> None:
        logger.error(
            f"Task {self.name} [{task_id}] failed: {exc}",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "args": args,
                "kwargs": kwargs,
            },
        )

    def on_success(
        self,
        retval: Any,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:
        logger.info(
            f"Task {self.name} [{task_id}] succeeded",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "retval": retval,
            },
        )

    def on_retry(
        self,
        exc: Exception,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        logger.warning(
            f"Task {self.name} [{task_id}] retry: {exc}",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "exception": str(exc),
                "retry_count": self.request.retries,
            },
        )


# Use CallbackTask as the default Task base
celery_app.Task = CallbackTask
