"""Promise-to-Pay lifecycle checks.

Runs periodically: sends a reminder ~24h before the promised date, and marks a
promise broken once the date passes without resolution (with a PROMISE_BROKEN audit
entry — a broken promise raises the customer's risk in future scoring).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_event
from app.core.logging import get_logger
from app.models import enums
from app.models.entities import PromiseToPay

log = get_logger(__name__)
ACTOR = "ptp-tracker@1.0.0"


async def check_promises(session: AsyncSession, *, today: date | None = None) -> dict:
    today = today or datetime.now(UTC).date()
    now = datetime.now(UTC)
    reminders = broken = 0

    rows = await session.execute(
        select(PromiseToPay).where(PromiseToPay.status == enums.PTPStatus.active)
    )
    for ptp in rows.scalars().all():
        if ptp.promised_date < today:
            ptp.status = enums.PTPStatus.broken
            ptp.resolved_at = now
            await write_audit_event(
                session, event_type="PROMISE_BROKEN", actor=ACTOR, merchant_id=ptp.merchant_id,
                entity_type="PromiseToPay", entity_id=ptp.ptp_id,
                payload={
                    "customer_id": ptp.customer_id,
                    "promised_date": ptp.promised_date.isoformat(),
                },
            )
            broken += 1
        elif ptp.promised_date <= today + timedelta(days=1) and ptp.reminder_sent_at is None:
            ptp.reminder_sent_at = now
            await write_audit_event(
                session, event_type="PROMISE_REMINDER_SENT", actor=ACTOR,
                merchant_id=ptp.merchant_id, entity_type="PromiseToPay", entity_id=ptp.ptp_id,
                payload={
                    "customer_id": ptp.customer_id,
                    "promised_date": ptp.promised_date.isoformat(),
                },
            )
            reminders += 1

    await session.commit()
    log.info("check_promises.done", reminders=reminders, broken=broken)
    return {"reminders_sent": reminders, "broken": broken}
