"""Celery task that runs the agent orchestrator for a detected RiskEvent."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.agents.orchestrator import orchestrate
from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


async def _run(risk_event_id: str) -> str | None:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with maker() as session:
            state = await orchestrate(session, uuid.UUID(risk_event_id))
            return state.outcome if state else None
    finally:
        await engine.dispose()


@celery_app.task(name="aria.orchestrate", bind=True, max_retries=2, default_retry_delay=10)
def orchestrate_task(self, risk_event_id: str) -> str | None:  # noqa: ANN001
    try:
        outcome = asyncio.run(_run(risk_event_id))
        log.info("orchestrate_task.done", risk_event_id=risk_event_id, outcome=outcome)
        return outcome
    except Exception as exc:  # noqa: BLE001
        log.error("orchestrate_task.error", risk_event_id=risk_event_id, error=str(exc))
        raise self.retry(exc=exc) from exc
