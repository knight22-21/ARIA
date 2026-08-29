"""Outcome Tracker — attributes recoveries to interventions.

Runs periodically (Celery Beat) or on demand. For every in-progress RiskEvent that
has had an intervention dispatched, it looks for a successful payment.captured event
for the same customer within the attribution window:

  - direct (1.0)   — captured amount ≈ the at-risk amount → ARIA's action recovered it
  - assisted (0.5) — a payment landed in-window but amount differs → partial credit
  - unrecovered    — the window expired with no captured payment

Writes a RecoveryRecord + OUTCOME_DETECTED / RECOVERY_ATTRIBUTED audit rows and
transitions the RiskEvent to recovered / unrecovered.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_event
from app.core.logging import get_logger
from app.models import enums
from app.models.entities import (
    InterventionPlan,
    PaymentEvent,
    RecoveryRecord,
    RiskEvent,
)

log = get_logger(__name__)
ACTOR = "outcome-tracker@1.0.0"
DEFAULT_WINDOW_HOURS = 48


async def _executed_plans(session: AsyncSession, risk_event_id) -> list[InterventionPlan]:
    rows = await session.execute(
        select(InterventionPlan).where(
            InterventionPlan.risk_event_id == risk_event_id,
            InterventionPlan.executed_at.is_not(None),
        )
    )
    return list(rows.scalars().all())


async def _find_capture(
    session: AsyncSession, risk: RiskEvent, customer_id: str, start: datetime, end: datetime
) -> PaymentEvent | None:
    rows = await session.execute(
        select(PaymentEvent)
        .where(
            PaymentEvent.merchant_id == risk.merchant_id,
            PaymentEvent.customer_id == customer_id,
            PaymentEvent.event_type == enums.EventType.payment_captured,
            PaymentEvent.received_at >= start,
            PaymentEvent.received_at <= end,
        )
        .order_by(PaymentEvent.received_at.asc())
    )
    return rows.scalars().first()


async def _cost_for_risk(session: AsyncSession, risk_event_id) -> int:
    total = await session.scalar(
        select(func.coalesce(func.sum(InterventionPlan.estimated_cost_paise), 0)).where(
            InterventionPlan.risk_event_id == risk_event_id
        )
    )
    return int(total or 0)


async def attribute_recovery_for_risk(
    session: AsyncSession,
    risk_event_id,
    *,
    amount_paise: int,
    captured_event_id=None,
) -> bool:
    """Directly attribute a recovery to a specific risk event (used by the real
    Razorpay capture webhook, where notes carry the risk-event id). Returns True if
    a new recovery was recorded."""
    risk = await session.get(RiskEvent, risk_event_id)
    if risk is None or risk.status == enums.RiskStatus.recovered:
        return False

    plan = (
        await session.execute(
            select(InterventionPlan).where(InterventionPlan.risk_event_id == risk_event_id)
        )
    ).scalars().first()
    cost = await _cost_for_risk(session, risk_event_id)
    now = datetime.now(UTC)

    session.add(
        RecoveryRecord(
            plan_id=plan.plan_id if plan else None,
            risk_event_id=risk_event_id,
            outcome=enums.RecoveryOutcome.recovered,
            recovered_amount_paise=amount_paise or risk.amount_at_risk_paise,
            payment_event_id_recovered=captured_event_id,
            attribution_confidence=1.0,
            recovery_cost_paise=cost,
            recovered_at=now,
        )
    )
    risk.status = enums.RiskStatus.recovered
    risk.resolved_at = now
    await write_audit_event(
        session, event_type="OUTCOME_DETECTED", actor="razorpay-webhook@1.0.0",
        merchant_id=risk.merchant_id, entity_type="RiskEvent", entity_id=risk_event_id,
        correlation_id=risk_event_id,
        payload={"outcome": "recovered", "source": "razorpay_capture"},
    )
    await write_audit_event(
        session, event_type="RECOVERY_ATTRIBUTED", actor="razorpay-webhook@1.0.0",
        merchant_id=risk.merchant_id, entity_type="RiskEvent", entity_id=risk_event_id,
        correlation_id=risk_event_id,
        payload={
            "recovered_amount_paise": amount_paise or risk.amount_at_risk_paise,
            "attribution_confidence": 1.0,
            "recovery_cost_paise": cost,
            "source": "razorpay_capture",
        },
    )
    await session.commit()
    log.info("attribute_recovery.direct", risk_event_id=str(risk_event_id))
    return True


async def track_outcomes(session: AsyncSession, *, now: datetime | None = None) -> dict:
    """Scan in-progress risk events and resolve those whose outcome is known."""
    now = now or datetime.now(UTC)
    stats = {"scanned": 0, "recovered": 0, "unrecovered": 0, "pending": 0}

    rows = await session.execute(
        select(RiskEvent).where(RiskEvent.status == enums.RiskStatus.in_progress)
    )
    risks = list(rows.scalars().all())

    for risk in risks:
        stats["scanned"] += 1
        plans = await _executed_plans(session, risk.risk_event_id)
        if not plans:
            stats["pending"] += 1
            continue

        intervention_time = min(p.executed_at for p in plans)
        window_h = max((p.attribution_window_hours or DEFAULT_WINDOW_HOURS) for p in plans)
        window_end = intervention_time + timedelta(hours=window_h)

        pe = (
            await session.get(PaymentEvent, risk.payment_event_id)
            if risk.payment_event_id
            else None
        )
        customer_id = pe.customer_id if pe else None

        capture = (
            await _find_capture(session, risk, customer_id, intervention_time, window_end)
            if customer_id
            else None
        )

        if capture is not None:
            amount = capture.amount_paise
            direct = amount >= int(risk.amount_at_risk_paise * 0.9)
            confidence = 1.0 if direct else 0.5
            cost = await _cost_for_risk(session, risk.risk_event_id)

            session.add(
                RecoveryRecord(
                    plan_id=plans[0].plan_id,
                    risk_event_id=risk.risk_event_id,
                    outcome=enums.RecoveryOutcome.recovered,
                    recovered_amount_paise=amount,
                    payment_event_id_recovered=capture.event_id,
                    attribution_confidence=confidence,
                    recovery_cost_paise=cost,
                    recovered_at=capture.received_at,
                )
            )
            risk.status = enums.RiskStatus.recovered
            risk.resolved_at = capture.received_at
            await write_audit_event(
                session, event_type="OUTCOME_DETECTED", actor=ACTOR,
                merchant_id=risk.merchant_id, entity_type="RiskEvent", entity_id=risk.risk_event_id,
                payload={"outcome": "recovered", "captured_payment_id": str(capture.event_id)},
            )
            await write_audit_event(
                session, event_type="RECOVERY_ATTRIBUTED", actor=ACTOR,
                merchant_id=risk.merchant_id, entity_type="RiskEvent", entity_id=risk.risk_event_id,
                payload={
                    "recovered_amount_paise": amount,
                    "attribution_confidence": confidence,
                    "recovery_cost_paise": cost,
                },
            )
            stats["recovered"] += 1

        elif now > window_end:
            cost = await _cost_for_risk(session, risk.risk_event_id)
            session.add(
                RecoveryRecord(
                    plan_id=plans[0].plan_id,
                    risk_event_id=risk.risk_event_id,
                    outcome=enums.RecoveryOutcome.unrecovered,
                    recovered_amount_paise=0,
                    attribution_confidence=0.0,
                    recovery_cost_paise=cost,
                    recovered_at=None,
                )
            )
            risk.status = enums.RiskStatus.unrecovered
            risk.resolved_at = now
            await write_audit_event(
                session, event_type="OUTCOME_DETECTED", actor=ACTOR,
                merchant_id=risk.merchant_id, entity_type="RiskEvent", entity_id=risk.risk_event_id,
                payload={"outcome": "unrecovered", "window_hours": window_h},
            )
            stats["unrecovered"] += 1
        else:
            stats["pending"] += 1

    await session.commit()
    log.info("track_outcomes.done", **stats)
    return stats
