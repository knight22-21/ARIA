"""Human-in-the-loop escalation queue + approve/reject actions."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.diagnostic import run_diagnostic
from app.agents.intervention import run_intervention
from app.core.audit import write_audit_event
from app.core.db import get_session
from app.execution.dispatcher import execute_plan
from app.models import enums
from app.models.entities import AuditEvent, Diagnosis, Merchant, RiskEvent
from app.schemas.agent import DiagnosisResult

router = APIRouter(prefix="/v1/escalations", tags=["escalations"])


def _diag_result_from_row(row: Diagnosis) -> DiagnosisResult:
    return DiagnosisResult(
        reasoning=row.reasoning_chain or "",
        root_cause_category=row.root_cause_category,
        confidence=row.confidence,
        evidence=(row.evidence_signals or {}).get("evidence", []),
        recommended_intervention_class=row.recommended_intervention_class or "",
        urgency_score=row.urgency_score,
    )


@router.get("")
async def list_escalations(session: AsyncSession = Depends(get_session)) -> list[dict]:
    """The Action Queue: escalated risk events + their escalation details."""
    risks = (
        await session.execute(
            select(RiskEvent)
            .where(RiskEvent.status == enums.RiskStatus.escalated)
            .order_by(RiskEvent.amount_at_risk_paise.desc())
        )
    ).scalars().all()

    out = []
    for risk in risks:
        esc = (
            await session.execute(
                select(AuditEvent)
                .where(
                    AuditEvent.entity_id == risk.risk_event_id,
                    AuditEvent.event_type == "ESCALATION_RAISED",
                )
                .order_by(AuditEvent.created_at.desc())
            )
        ).scalars().first()
        payload = esc.payload if esc else {}
        out.append(
            {
                "risk_event_id": str(risk.risk_event_id),
                "workflow_type": risk.workflow_type.value,
                "amount_at_risk_paise": risk.amount_at_risk_paise,
                "urgency": payload.get("urgency"),
                "summary": payload.get("summary"),
                "recommended_action": payload.get("recommended_action"),
                "reason": payload.get("reason_escalated"),
            }
        )
    return out


class RejectBody(BaseModel):
    reason: str


@router.post("/{risk_event_id}/approve")
async def approve(risk_event_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    """Human approves ARIA proceeding — runs diagnosis (if needed) → intervention → execute.

    The amount-ceiling policy gate is intentionally bypassed here: a human has approved.
    """
    risk = await session.get(RiskEvent, risk_event_id)
    if risk is None:
        raise HTTPException(status_code=404, detail="risk event not found")
    if risk.status != enums.RiskStatus.escalated:
        raise HTTPException(status_code=409, detail=f"not in escalated state ({risk.status.value})")

    merchant = await session.get(Merchant, risk.merchant_id)
    config = (merchant.config if merchant else {}) or {}

    diag_row = (
        await session.execute(select(Diagnosis).where(Diagnosis.risk_event_id == risk_event_id))
    ).scalars().first()
    if diag_row is None:
        diag_result, diag_row = await run_diagnostic(session, risk)
    else:
        diag_result = _diag_result_from_row(diag_row)

    interv_result, plan = await run_intervention(
        session, risk, diag_row, diag_result, config, human_approved=True
    )
    risk.status = enums.RiskStatus.in_progress
    await execute_plan(session, plan.plan_id)

    risk = await session.get(RiskEvent, risk_event_id)
    await write_audit_event(
        session, event_type="HUMAN_APPROVED", actor="human:ops", merchant_id=risk.merchant_id,
        entity_type="RiskEvent", entity_id=risk.risk_event_id,
        payload={"action_type": interv_result.action_type.value, "plan_id": str(plan.plan_id)},
    )
    await session.commit()
    return {
        "risk_event_id": str(risk_event_id),
        "approved": True,
        "action_type": interv_result.action_type.value,
        "channel": interv_result.channel.value if interv_result.channel else None,
    }


@router.post("/{risk_event_id}/reject")
async def reject(
    risk_event_id: uuid.UUID, body: RejectBody, session: AsyncSession = Depends(get_session)
) -> dict:
    if not body.reason.strip():
        raise HTTPException(status_code=400, detail="reason is required")
    risk = await session.get(RiskEvent, risk_event_id)
    if risk is None:
        raise HTTPException(status_code=404, detail="risk event not found")
    if risk.status != enums.RiskStatus.escalated:
        raise HTTPException(status_code=409, detail=f"not in escalated state ({risk.status.value})")

    risk.status = enums.RiskStatus.suppressed
    await write_audit_event(
        session, event_type="HUMAN_REJECTED", actor="human:ops", merchant_id=risk.merchant_id,
        entity_type="RiskEvent", entity_id=risk.risk_event_id, payload={"reason": body.reason},
    )
    await session.commit()
    return {"risk_event_id": str(risk_event_id), "rejected": True, "reason": body.reason}
