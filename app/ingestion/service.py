"""The single ingestion entrypoint both paths converge on.

Razorpay webhooks (Path A) and the synthetic injector (Path B) each normalize to
``PaymentEventIn`` and call ``ingest_payment_event``. Nothing downstream knows or
cares which path produced the event.

Flow: resolve merchant → idempotency guard (Redis) → persist PaymentEvent →
record bank-rate stats → run detection (inline) or enqueue a Celery task.
"""

from __future__ import annotations

import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bootstrap import resolve_merchant_id
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.detection import bank_rate
from app.detection.engine import run_detection
from app.models import enums
from app.models.entities import PaymentEvent, RiskEvent
from app.schemas.payment import PaymentEventIn

log = get_logger(__name__)

_IDEMPOTENCY_TTL = 24 * 3600  # Razorpay retries webhooks up to 24h

_NON_FAILURE = {enums.EventType.payment_captured, enums.EventType.subscription_charged}


async def _already_seen(gateway_event_id: str | None) -> bool:
    """Return True (and mark) if this gateway event was already ingested."""
    if not gateway_event_id:
        return False
    r = get_redis()
    key = f"aria:idem:{gateway_event_id}"
    # SET NX returns True only if the key was newly set.
    was_set = await r.set(key, "1", nx=True, ex=_IDEMPOTENCY_TTL)
    return not was_set


async def ingest_payment_event(
    session: AsyncSession, payload: PaymentEventIn, *, inline: bool = True
) -> tuple[PaymentEvent | None, RiskEvent | None]:
    """Persist a normalized payment event and kick off detection.

    Returns (payment_event, risk_event). ``risk_event`` is populated only when
    ``inline`` and the event scored at/above threshold; otherwise detection runs
    asynchronously via Celery and risk_event is None.
    """
    if await _already_seen(payload.gateway_event_id):
        log.info("ingest.duplicate", gateway_event_id=payload.gateway_event_id)
        return None, None

    merchant_id = await resolve_merchant_id(session, payload.merchant_id)

    pe = PaymentEvent(
        merchant_id=merchant_id,
        gateway=payload.gateway,
        gateway_event_id=payload.gateway_event_id,
        event_type=payload.event_type,
        amount_paise=payload.amount_paise,
        currency=payload.currency,
        customer_id=payload.customer_id,
        customer_phone=payload.customer_phone,
        customer_email=payload.customer_email,
        payment_method=payload.payment_method,
        error_code=payload.error_code,
        error_description=payload.error_description,
        raw_payload=payload.raw_payload,
    )
    session.add(pe)
    await session.commit()
    await session.refresh(pe)

    # Feed the bank-failure-rate aggregator (both success and failure count).
    bank = (payload.payment_method or {}).get("bank", "")
    if bank:
        await bank_rate.record_payment(
            str(merchant_id),
            bank,
            failed=payload.event_type not in _NON_FAILURE,
            now_epoch=time.time(),
        )

    log.info(
        "ingest.persisted",
        payment_event_id=str(pe.event_id),
        event_type=payload.event_type.value,
        gateway=payload.gateway.value,
    )

    if inline:
        risk = await run_detection(session, pe.event_id)
        return pe, risk

    # Async path: hand off to the Celery worker.
    from app.tasks.detection import detect_task

    detect_task.delay(str(pe.event_id))
    return pe, None
