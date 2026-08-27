"""Dashboard support APIs — summary stats + global audit query."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.entities import (
    AuditEvent,
    Diagnosis,
    InterventionPlan,
    Outbox,
    PaymentEvent,
    PromiseToPay,
    RiskEvent,
)

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


@router.get("/customers/{customer_id}/export")
async def data_subject_export(
    customer_id: str, session: AsyncSession = Depends(get_session)
) -> dict:
    """DPDP-style data-subject access: export everything ARIA holds for a customer.

    PII is decrypted here by design — this endpoint fulfils the customer's own
    right of access. Restrict to authorized callers in production.
    """
    pe_rows = (
        await session.execute(
            select(PaymentEvent).where(PaymentEvent.customer_id == customer_id)
        )
    ).scalars().all()
    pe_ids = [p.event_id for p in pe_rows]

    risks = (
        (
            await session.execute(
                select(RiskEvent).where(RiskEvent.payment_event_id.in_(pe_ids))
            )
        ).scalars().all()
        if pe_ids
        else []
    )
    risk_ids = [r.risk_event_id for r in risks]

    diagnoses = (
        (
            await session.execute(select(Diagnosis).where(Diagnosis.risk_event_id.in_(risk_ids)))
        ).scalars().all()
        if risk_ids
        else []
    )
    plans = (
        (
            await session.execute(
                select(InterventionPlan).where(InterventionPlan.risk_event_id.in_(risk_ids))
            )
        ).scalars().all()
        if risk_ids
        else []
    )
    ptps = (
        await session.execute(select(PromiseToPay).where(PromiseToPay.customer_id == customer_id))
    ).scalars().all()

    return {
        "customer_id": customer_id,
        "exported_at": None,  # stamp at the edge if needed
        "payment_events": [
            {
                "event_id": str(p.event_id),
                "event_type": p.event_type.value,
                "amount_paise": p.amount_paise,
                "phone": p.customer_phone,  # decrypted
                "email": p.customer_email,  # decrypted
                "received_at": p.received_at.isoformat(),
            }
            for p in pe_rows
        ],
        "risk_events": [
            {
                "risk_event_id": str(r.risk_event_id),
                "workflow": r.workflow_type.value,
                "status": r.status.value,
            }
            for r in risks
        ],
        "diagnoses": [
            {"root_cause": d.root_cause_category, "confidence": d.confidence} for d in diagnoses
        ],
        "interventions": [
            {"action_type": pl.action_type.value, "message_content": pl.message_content}
            for pl in plans
        ],
        "promises_to_pay": [
            {"promised_amount_paise": t.promised_amount_paise, "status": t.status.value}
            for t in ptps
        ],
    }
