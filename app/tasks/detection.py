"""Celery task wrapping the async detection engine.

The Celery worker is synchronous and runs each task in a fresh event loop via
``asyncio.run``. To avoid asyncpg's "attached to a different loop" error, we build
a short-lived engine (NullPool) per task rather than reusing the app-wide pool.
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.logging import get_logger
from app.detection.engine import run_detection

log = get_logger(__name__)


async def _run(payment_event_id: str) -> str | None:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with maker() as session:
            risk = await run_detection(session, uuid.UUID(payment_event_id))
            return str(risk.risk_event_id) if risk else None
    finally:
        await engine.dispose()


@celery_app.task(name="aria.detect", bind=True, max_retries=3, default_retry_delay=5)
def detect_task(self, payment_event_id: str) -> str | None:  # noqa: ANN001
    try:
        risk_id = asyncio.run(_run(payment_event_id))
        log.info("detect_task.done", payment_event_id=payment_event_id, risk_event_id=risk_id)
        return risk_id
    except Exception as exc:  # noqa: BLE001
        log.error("detect_task.error", payment_event_id=payment_event_id, error=str(exc))
        raise self.retry(exc=exc) from exc
