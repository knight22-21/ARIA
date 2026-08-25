"""Outbox viewer API — rendered messages (never actually sent)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import enums
from app.models.entities import Outbox
from app.schemas.outbox import OutboxOut

router = APIRouter(prefix="/v1/outbox", tags=["outbox"])


@router.get("", response_model=list[OutboxOut])
async def list_outbox(
    session: AsyncSession = Depends(get_session),
    channel: enums.Channel | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Outbox]:
    stmt = select(Outbox).order_by(Outbox.created_at.desc()).limit(limit)
    if channel is not None:
        stmt = stmt.where(Outbox.channel == channel)
    return list((await session.execute(stmt)).scalars().all())
