"""Celery Beat task: Promise-to-Pay reminders + broken-promise detection."""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.logging import get_logger
from app.execution.promises import check_promises

log = get_logger(__name__)


async def _run() -> dict:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with maker() as session:
            return await check_promises(session)
    finally:
        await engine.dispose()


@celery_app.task(name="aria.check_promises")
def check_promises_task() -> dict:
    stats = asyncio.run(_run())
    log.info("check_promises_task.done", **stats)
    return stats
