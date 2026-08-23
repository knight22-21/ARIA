"""Recovery P&L computation (blueprint §14.1).

A true P&L for the recovery operation: gross at risk, interventions attempted,
attributed recovery (direct 1.0 + assisted 0.5), cost of recovery, net, and the
efficiency ratios. Reports both gross-recovered and attribution-weighted figures
so evaluators see the conservative and optimistic bounds.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import enums
from app.models.entities import InterventionPlan, RecoveryRecord, RiskEvent


def _rupees(paise: int) -> float:
    return round((paise or 0) / 100, 2)


async def compute_pnl(
    session: AsyncSession,
    *,
    merchant_id: uuid.UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict:
    def scope(stmt, ts_col):
        if merchant_id is not None:
            stmt = stmt.where(RiskEvent.merchant_id == merchant_id)
        if since is not None:
            stmt = stmt.where(ts_col >= since)
        if until is not None:
            stmt = stmt.where(ts_col <= until)
        return stmt

    # Gross revenue at risk (all detected risk events in the period).
    # NOTE: Postgres SUM(bigint) → numeric → Decimal; coerce to int to avoid
    # float/Decimal type errors downstream.
    gross = int(
        await session.scalar(
            scope(
                select(func.coalesce(func.sum(RiskEvent.amount_at_risk_paise), 0)).select_from(
                    RiskEvent
                ),
                RiskEvent.detected_at,
            )
        )
        or 0
    )

    # Interventions attempted (auto) and escalations.
    auto_interventions = await session.scalar(
        scope(
            select(func.count())
            .select_from(InterventionPlan)
            .join(RiskEvent, InterventionPlan.risk_event_id == RiskEvent.risk_event_id)
            .where(InterventionPlan.executed_at.is_not(None)),
            RiskEvent.detected_at,
        )
    ) or 0
    escalated = await session.scalar(
        scope(
            select(func.count())
            .select_from(RiskEvent)
            .where(RiskEvent.status == enums.RiskStatus.escalated),
            RiskEvent.detected_at,
        )
    ) or 0

    # Recovery records joined to risk (for period/merchant scoping).
    rec_rows = (
        await session.execute(
            scope(
                select(RecoveryRecord, RiskEvent.workflow_type)
                .select_from(RecoveryRecord)
                .join(RiskEvent, RecoveryRecord.risk_event_id == RiskEvent.risk_event_id),
                RiskEvent.detected_at,
            )
        )
    ).all()

    recovered_gross = 0
    recovered_direct = 0
    recovered_assisted = 0
    recovered_attributed = 0.0
    total_cost = 0
    by_workflow: dict[str, dict] = {}

    for rec, workflow in rec_rows:
        total_cost += rec.recovery_cost_paise or 0
        wf = by_workflow.setdefault(
            workflow.value, {"recovered_paise": 0, "attributed_paise": 0.0, "count": 0}
        )
        if rec.outcome == enums.RecoveryOutcome.recovered:
            amt = rec.recovered_amount_paise or 0
            recovered_gross += amt
            attributed = amt * rec.attribution_confidence
            recovered_attributed += attributed
            if rec.attribution_confidence >= 1.0:
                recovered_direct += amt
            else:
                recovered_assisted += amt
            wf["recovered_paise"] += amt
            wf["attributed_paise"] += attributed
            wf["count"] += 1

    # Add cost of executed interventions that have no recovery record yet (still pending).
    pending_cost = int(
        await session.scalar(
            scope(
                select(func.coalesce(func.sum(InterventionPlan.estimated_cost_paise), 0))
                .select_from(InterventionPlan)
                .join(RiskEvent, InterventionPlan.risk_event_id == RiskEvent.risk_event_id)
                .where(
                    InterventionPlan.executed_at.is_not(None),
                    RiskEvent.status == enums.RiskStatus.in_progress,
                ),
                RiskEvent.detected_at,
            )
        )
        or 0
    )
    total_cost += pending_cost

    net = recovered_attributed - total_cost
    recovery_rate = (recovered_attributed / gross) if gross else 0.0
    margin = (net / recovered_attributed) if recovered_attributed else 0.0
    cost_per_rupee = (total_cost / recovered_attributed) if recovered_attributed else 0.0

    return {
        "gross_revenue_at_risk": _rupees(gross),
        "interventions": {"auto": auto_interventions, "escalated": escalated},
        "recovered": {
            "direct": _rupees(recovered_direct),
            "assisted": _rupees(recovered_assisted),
            "gross": _rupees(recovered_gross),
            "attributed": _rupees(round(recovered_attributed)),
        },
        "cost": {"total": _rupees(total_cost)},
        "net_recovered": _rupees(round(net)),
        "recovery_rate_pct": round(recovery_rate * 100, 1),
        "recovery_margin_pct": round(margin * 100, 1),
        "cost_per_rupee_recovered": round(cost_per_rupee, 4),
        "by_workflow": {
            k: {
                "recovered": _rupees(v["recovered_paise"]),
                "attributed": _rupees(round(v["attributed_paise"])),
                "count": v["count"],
            }
            for k, v in by_workflow.items()
        },
    }
