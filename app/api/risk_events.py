"""Risk-event query API (Phase 1 read surface)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import enums
from app.models.entities import RiskEvent
from app.schemas.risk import RiskEventOut

router = APIRouter(prefix="/v1/risk-events", tags=["risk-events"])


@router.get("", response_model=list[RiskEventOut])
async def list_risk_events(
    session: AsyncSession = Depends(get_session),
    status: enums.RiskStatus | None = None,
    workflow: enums.WorkflowType | None = None,
    min_amount_paise: int | None = Query(default=None, ge=0),
    max_amount_paise: int | None = Query(default=None, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[RiskEvent]:
    stmt = select(RiskEvent).order_by(RiskEvent.detected_at.desc())
    if status is not None:
        stmt = stmt.where(RiskEvent.status == status)
    if workflow is not None:
        stmt = stmt.where(RiskEvent.workflow_type == workflow)
    if min_amount_paise is not None:
        stmt = stmt.where(RiskEvent.amount_at_risk_paise >= min_amount_paise)
    if max_amount_paise is not None:
        stmt = stmt.where(RiskEvent.amount_at_risk_paise <= max_amount_paise)
    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{risk_event_id}", response_model=RiskEventOut)
async def get_risk_event(
    risk_event_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> RiskEvent:
    risk = await session.get(RiskEvent, risk_event_id)
    if risk is None:
        raise HTTPException(status_code=404, detail="risk event not found")
    return risk
