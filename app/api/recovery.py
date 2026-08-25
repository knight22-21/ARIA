"""Recovery P&L API."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.pnl import compute_pnl
from app.core.db import get_session
from app.models.entities import RiskEvent

router = APIRouter(prefix="/v1/recovery", tags=["recovery"])


@router.get("/p-and-l")
async def recovery_pnl(
    session: AsyncSession = Depends(get_session),
    merchant_id: uuid.UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict:
    return await compute_pnl(session, merchant_id=merchant_id, since=since, until=until)


# Human-readable labels for Sankey nodes.
_STATUS_LABEL = {
    "detected": "Detected",
    "in_progress": "In Progress",
    "recovered": "Recovered",
    "unrecovered": "Unrecovered",
    "escalated": "Escalated",
    "suppressed": "Suppressed",
}
_WORKFLOW_LABEL = {
    "payment_degradation": "Payment",
    "checkout_abandonment": "Checkout",
    "subscription_failure": "Subscription",
    "b2b_receivable": "B2B Invoice",
    "mandate_retry": "Mandate",
}


@router.get("/sankey")
async def recovery_sankey(session: AsyncSession = Depends(get_session)) -> dict:
    """Flow of ₹ at risk → workflow → outcome, for a Nivo Sankey diagram."""
    rows = (
        await session.execute(
            select(
                RiskEvent.workflow_type,
                RiskEvent.status,
                func.count(),
                func.coalesce(func.sum(RiskEvent.amount_at_risk_paise), 0),
            ).group_by(RiskEvent.workflow_type, RiskEvent.status)
        )
    ).all()

    nodes: dict[str, str] = {"At Risk": "At Risk"}
    links: list[dict] = []
    src_totals: dict[str, int] = {}

    for workflow, status, _count, amt in rows:
        amount_rupees = int(amt) // 100
        if amount_rupees <= 0:
            continue
        wf_label = _WORKFLOW_LABEL.get(workflow.value, workflow.value)
        st_label = _STATUS_LABEL.get(status.value, status.value)
        nodes[wf_label] = wf_label
        nodes[st_label] = st_label
        # At Risk → workflow (accumulate)
        src_totals[wf_label] = src_totals.get(wf_label, 0) + amount_rupees
        # workflow → status
        links.append({"source": wf_label, "target": st_label, "value": amount_rupees})

    at_risk_links = [
        {"source": "At Risk", "target": wf, "value": val} for wf, val in src_totals.items()
    ]

    return {
        "nodes": [{"id": n} for n in nodes],
        "links": at_risk_links + links,
    }
