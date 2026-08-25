"""Celery application — broker/result backend on Redis.

Used for: detection scans, scheduled retries, outcome tracking.
Beat schedule (redbeat) is wired up in later phases.
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "aria",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    # RedBeat scheduler for reliable, Redis-backed periodic tasks.
    redbeat_redis_url=settings.redis_url,
    beat_scheduler="redbeat.RedBeatScheduler",
    # Task modules the worker imports on boot (avoids import cycles at module load).
    imports=(
        "app.tasks.detection",
        "app.tasks.orchestration",
        "app.tasks.outcome",
        "app.tasks.promises",
    ),
    beat_schedule={
        # Outcome Tracker sweeps for attributable recoveries on a short cadence.
        "outcome-tracker": {"task": "aria.track_outcomes", "schedule": 30.0},
        # Promise-to-Pay reminders + broken-promise detection (hourly in prod).
        "ptp-checker": {"task": "aria.check_promises", "schedule": 3600.0},
    },
)


@celery_app.task(name="aria.ping")
def ping() -> str:
    """Trivial task to verify the worker is alive."""
    return "pong"
