"""Celery Beat task: run the Outcome Tracker periodically."""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.logging import get_logger
from app.execution.outcome import track_outcomes

log = get_logger(__name__)


async def _run() -> dict:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with maker() as session:
            return await track_outcomes(session)
    finally:
        await engine.dispose()


@celery_app.task(name="aria.track_outcomes")
def track_outcomes_task() -> dict:
    stats = asyncio.run(_run())
    log.info("track_outcomes_task.done", **stats)
    return stats
