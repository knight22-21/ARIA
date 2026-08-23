"""Risk-event query API (Phase 1 read surface)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import enums
from app.models.entities import AuditEvent, Diagnosis, InterventionPlan, RiskEvent
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


@router.get("/{risk_event_id}/trail")
async def get_risk_trail(
    risk_event_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> dict:
    """Full lifecycle: diagnosis (with reasoning), plans, and the audit timeline."""
    risk = await session.get(RiskEvent, risk_event_id)
    if risk is None:
        raise HTTPException(status_code=404, detail="risk event not found")

    diag = (
        await session.execute(
            select(Diagnosis).where(Diagnosis.risk_event_id == risk_event_id)
        )
    ).scalars().first()

    plans = (
        await session.execute(
            select(InterventionPlan).where(InterventionPlan.risk_event_id == risk_event_id)
        )
    ).scalars().all()

    # Reconstruct the full lifecycle: audit rows for the risk event AND its
    # child entities (diagnosis, intervention plans), ordered chronologically.
    related_ids = [risk_event_id]
    if diag is not None:
        related_ids.append(diag.diagnosis_id)
    related_ids.extend(p.plan_id for p in plans)
    audit = (
        await session.execute(
            select(AuditEvent)
            .where(AuditEvent.entity_id.in_(related_ids))
            .order_by(AuditEvent.created_at.asc())
        )
    ).scalars().all()

    return {
        "risk_event": {
            "risk_event_id": str(risk.risk_event_id),
            "status": risk.status.value,
            "workflow_type": risk.workflow_type.value,
            "risk_score": risk.risk_score,
            "amount_at_risk_paise": risk.amount_at_risk_paise,
        },
        "diagnosis": None
        if diag is None
        else {
            "root_cause_category": diag.root_cause_category,
            "confidence": diag.confidence,
            "reasoning_chain": diag.reasoning_chain,
            "recommended_intervention_class": diag.recommended_intervention_class,
            "urgency_score": diag.urgency_score,
            "llm_model": diag.llm_model,
            "prompt_version": diag.llm_prompt_version,
        },
        "interventions": [
            {
                "action_type": p.action_type.value,
                "channel": p.channel.value if p.channel else None,
                "message_content": p.message_content,
                "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
                "estimated_cost_paise": p.estimated_cost_paise,
                "status": p.status.value,
            }
            for p in plans
        ],
        "audit": [
            {
                "event_type": a.event_type,
                "actor": a.actor,
                "created_at": a.created_at.isoformat(),
                "payload": a.payload,
            }
            for a in audit
        ],
    }
