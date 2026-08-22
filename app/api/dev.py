"""Developer/demo endpoints (Path B — synthetic injector). Disabled outside dev."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.ingestion.scenarios import build_scenario, scenario_names
from app.ingestion.service import ingest_payment_event
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
    return {
        "payment_event_id": str(pe.event_id) if pe else None,
        "risk_event_id": str(risk.risk_event_id) if risk else None,
        "risk_score": risk.risk_score if risk else None,
        "workflow_type": risk.workflow_type.value if risk else None,
        "duplicate": pe is None,
    }
