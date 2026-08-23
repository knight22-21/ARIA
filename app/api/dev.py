"""Developer/demo endpoints (Path B — synthetic injector). Disabled outside dev."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import orchestrate
from app.core.config import settings
from app.core.db import get_session
from app.execution.outcome import track_outcomes
from app.ingestion.scenarios import build_scenario, scenario_names
from app.ingestion.service import ingest_payment_event
from app.models import enums
from app.schemas.payment import PaymentEventIn

router = APIRouter(prefix="/dev", tags=["dev"])


def _guard() -> None:
    if settings.aria_env == "production":
        raise HTTPException(status_code=404, detail="not found")


class InjectRequest(BaseModel):
    scenario: str | None = None
    event: PaymentEventIn | None = None
    inline: bool = True


@router.get("/scenarios")
async def list_scenarios() -> dict:
    _guard()
    return {"scenarios": scenario_names()}


@router.post("/inject")
async def inject(req: InjectRequest, session: AsyncSession = Depends(get_session)) -> dict:
    _guard()
    if req.scenario:
        try:
            payload = build_scenario(req.scenario)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    elif req.event:
        payload = req.event
    else:
        raise HTTPException(status_code=400, detail="provide 'scenario' or 'event'")

    pe, risk = await ingest_payment_event(session, payload, inline=req.inline)

    # Inline path also drives the agent pipeline so a single call shows the full run.
    state = None
    if req.inline and risk is not None:
        state = await orchestrate(session, risk.risk_event_id)

    resp: dict = {
        "payment_event_id": str(pe.event_id) if pe else None,
        "risk_event_id": str(risk.risk_event_id) if risk else None,
        "risk_score": risk.risk_score if risk else None,
        "workflow_type": risk.workflow_type.value if risk else None,
        "duplicate": pe is None,
    }
    if state is not None:
        resp["outcome"] = state.outcome
        if state.diagnosis:
            resp["diagnosis"] = {
                "root_cause_category": state.diagnosis.root_cause_category,
                "confidence": state.diagnosis.confidence,
                "recommended_intervention_class": state.diagnosis.recommended_intervention_class,
            }
        if state.intervention:
            resp["intervention"] = {
                "action_type": state.intervention.action_type.value,
                "channel": state.intervention.channel.value if state.intervention.channel else None,
                "message_preview": (state.intervention.message_content or "")[:160],
            }
        if state.escalation:
            resp["escalation"] = {
                "urgency": state.escalation.urgency.value,
                "reason": state.escalation.reason_escalated,
            }
    return resp


class CaptureRequest(BaseModel):
    """Simulate a successful payment (drives outcome attribution)."""

    customer_id: str
    amount_paise: int
    currency: str = "INR"


@router.post("/capture")
async def capture(req: CaptureRequest, session: AsyncSession = Depends(get_session)) -> dict:
    """Inject a payment.captured event for a customer (no risk event created)."""
    _guard()
    payload = PaymentEventIn(
        gateway=enums.Gateway.synthetic,
        event_type=enums.EventType.payment_captured,
        amount_paise=req.amount_paise,
        currency=req.currency,
        customer_id=req.customer_id,
    )
    pe, _ = await ingest_payment_event(session, payload, inline=True)
    return {"payment_event_id": str(pe.event_id) if pe else None, "event_type": "payment_captured"}


@router.post("/run-outcome-tracker")
async def run_outcome_tracker(session: AsyncSession = Depends(get_session)) -> dict:
    """Run the Outcome Tracker once (Celery Beat runs this on a schedule in prod)."""
    _guard()
    return await track_outcomes(session)
