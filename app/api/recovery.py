"""Recovery P&L API."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.pnl import compute_pnl
from app.core.db import get_session

router = APIRouter(prefix="/v1/recovery", tags=["recovery"])


@router.get("/p-and-l")
async def recovery_pnl(
    session: AsyncSession = Depends(get_session),
    merchant_id: uuid.UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict:
    return await compute_pnl(session, merchant_id=merchant_id, since=since, until=until)
