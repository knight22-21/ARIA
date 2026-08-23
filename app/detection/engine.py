"""Detection engine — turns a persisted PaymentEvent into a scored RiskEvent.

Assembles the six signal values (from taxonomy + Postgres history + Redis bank
rates), computes the weighted score, and — above threshold — creates a RiskEvent
and writes a RISK_DETECTED audit entry. Returns the RiskEvent, or None if the
event scored below threshold.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_event
from app.core.logging import get_logger
from app.detection import bank_rate, scorer
from app.detection.classifier import classify_workflow
from app.detection.taxonomy import classify_error
from app.models import enums
from app.models.entities import PaymentEvent, RiskEvent

log = get_logger(__name__)

RISK_THRESHOLD = 0.40

# Successful/neutral events never produce a RiskEvent (they drive outcome tracking).
_NON_RISK_EVENTS = {
    enums.EventType.payment_captured,
    enums.EventType.subscription_charged,
    enums.EventType.mandate_confirmed,
    enums.EventType.checkout_created,
}

# Event types that represent a failure/at-risk signal.
_FAILURE_EVENTS = {
    enums.EventType.payment_failed,
    enums.EventType.subscription_halted,
    enums.EventType.mandate_rejected,
    enums.EventType.checkout_abandoned,
    enums.EventType.invoice_overdue,
}


async def _customer_failure_rate_7d(
    session: AsyncSession, merchant_id: uuid.UUID, customer_id: str | None, now: datetime
) -> float:
    if not customer_id:
        return 0.0
    window = now - timedelta(days=7)
    total = await session.scalar(
        select(func.count())
        .select_from(PaymentEvent)
        .where(
            PaymentEvent.merchant_id == merchant_id,
            PaymentEvent.customer_id == customer_id,
            PaymentEvent.received_at >= window,
        )
    )
    if not total:
        return 0.0
    fails = await session.scalar(
        select(func.count())
        .select_from(PaymentEvent)
        .where(
            PaymentEvent.merchant_id == merchant_id,
            PaymentEvent.customer_id == customer_id,
            PaymentEvent.received_at >= window,
            PaymentEvent.event_type.in_(list(_FAILURE_EVENTS)),
        )
    )
    return (fails or 0) / total


async def _subscription_health(
    session: AsyncSession, merchant_id: uuid.UUID, customer_id: str | None, now: datetime
) -> float:
    """Consecutive subscription/mandate failures → higher = unhealthier (0..1)."""
    if not customer_id:
        return 0.0
    window = now - timedelta(days=90)
    fails = await session.scalar(
        select(func.count())
        .select_from(PaymentEvent)
        .where(
            PaymentEvent.merchant_id == merchant_id,
            PaymentEvent.customer_id == customer_id,
            PaymentEvent.received_at >= window,
            PaymentEvent.event_type.in_(
                [enums.EventType.subscription_halted, enums.EventType.mandate_rejected]
            ),
        )
    )
    return min(1.0, (fails or 0) / 3.0)


def _fraud_proxy(error_category: str) -> float:
    return {"fraud": 0.9, "hard_decline": 0.5}.get(error_category, 0.0)


async def run_detection(session: AsyncSession, payment_event_id: uuid.UUID) -> RiskEvent | None:
    """Score a payment event and, if at risk, create + persist a RiskEvent."""
    pe = await session.get(PaymentEvent, payment_event_id)
    if pe is None:
        log.warning("detection.missing_payment_event", payment_event_id=str(payment_event_id))
        return None

    # Successful/neutral events are not risks; they feed the Outcome Tracker.
    if pe.event_type in _NON_RISK_EVENTS:
        return None

    now = datetime.now(UTC)
    now_epoch = time.time()
    err = classify_error(pe.error_code)
    bank = (pe.payment_method or {}).get("bank", "")

    bank_fail_rate, _ = await bank_rate.failure_rate_1h(
        str(pe.merchant_id), bank, now_epoch=now_epoch
    )

    signal_values = {
        "error_code_severity": err.severity,
        "customer_failure_rate_7d": await _customer_failure_rate_7d(
            session, pe.merchant_id, pe.customer_id, now
        ),
        "bank_failure_rate_1h": bank_fail_rate,
        "amount_percentile": scorer.amount_percentile(pe.amount_paise),
        "subscription_health_score": await _subscription_health(
            session, pe.merchant_id, pe.customer_id, now
        ),
        "fraud_proxy_score": _fraud_proxy(err.category),
    }
    score, signals = scorer.compute_score(signal_values)
    workflow = classify_workflow(pe.event_type)

    log.info(
        "detection.scored",
        payment_event_id=str(payment_event_id),
        score=score,
        workflow=workflow.value,
        error_category=err.category,
    )

    if score < RISK_THRESHOLD:
        return None

    risk = RiskEvent(
        payment_event_id=pe.event_id,
        merchant_id=pe.merchant_id,
        risk_score=score,
        risk_signals=signals,
        workflow_type=workflow,
        status=enums.RiskStatus.detected,
        amount_at_risk_paise=pe.amount_paise,
    )
    session.add(risk)
    await session.flush()

    await write_audit_event(
        session,
        event_type="RISK_DETECTED",
        actor="detection-engine@0.1.0",
        merchant_id=pe.merchant_id,
        entity_type="RiskEvent",
        entity_id=risk.risk_event_id,
        payload={
            "risk_score": score,
            "workflow_type": workflow.value,
            "error_category": err.category,
            "amount_at_risk_paise": pe.amount_paise,
            "signals": signals,
        },
    )
    await session.commit()
    return risk
