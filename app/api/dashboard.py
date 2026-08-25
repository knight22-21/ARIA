"""Dashboard support APIs — summary stats + global audit query."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.entities import AuditEvent, Outbox, RiskEvent

router = APIRouter(prefix="/v1", tags=["dashboard"])


@router.get("/stats/summary")
async def summary(session: AsyncSession = Depends(get_session)) -> dict:
    """Counts by status + totals for the Command Center KPI strip."""
    rows = (
        await session.execute(
            select(
                RiskEvent.status,
                func.count(),
                func.coalesce(func.sum(RiskEvent.amount_at_risk_paise), 0),
            ).group_by(RiskEvent.status)
        )
    ).all()

    by_status = {
        status.value: {"count": count, "amount_paise": int(amt)}
        for status, count, amt in rows
    }
    total_events = sum(v["count"] for v in by_status.values())
    total_at_risk = sum(v["amount_paise"] for v in by_status.values())
    outbox_count = await session.scalar(select(func.count()).select_from(Outbox)) or 0

    return {
        "total_events": total_events,
        "total_at_risk_paise": total_at_risk,
        "by_status": by_status,
        "outbox_count": outbox_count,
    }


@router.get("/audit")
async def audit_query(
    session: AsyncSession = Depends(get_session),
    event_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset)
    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    if entity_id is not None:
        stmt = stmt.where(AuditEvent.entity_id == entity_id)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "audit_id": str(a.audit_id),
            "event_type": a.event_type,
            "actor": a.actor,
            "entity_type": a.entity_type,
            "entity_id": str(a.entity_id) if a.entity_id else None,
            "checksum": a.checksum[:12] + "…",
            "created_at": a.created_at.isoformat(),
            "payload": a.payload,
        }
        for a in rows
    ]
