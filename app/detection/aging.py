"""Invoice aging scanner.

Scans open invoices, and for each overdue one without an active RiskEvent, synthesizes
an ``invoice_overdue`` PaymentEvent (tagged with the aging bucket) and runs it through
detection + orchestration. Deduplicated via ``Invoice.has_active_risk``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.ingestion.service import ingest_payment_event
from app.models import enums
from app.models.entities import Invoice
from app.schemas.payment import PaymentEventIn

log = get_logger(__name__)


def aging_bucket(days_overdue: int) -> str:
    if days_overdue <= 0:
        return "current"
    if days_overdue <= 30:
        return "0-30"
    if days_overdue <= 60:
        return "31-60"
    if days_overdue <= 90:
        return "61-90"
    return "90+"


async def scan_invoices(session: AsyncSession, *, today: date | None = None) -> dict:
    """Emit RiskEvents for newly-overdue invoices. Returns a summary."""
    # Local import avoids a module-load cycle (aging → orchestrator → agents).
    from app.agents.orchestrator import orchestrate

    today = today or datetime.now(UTC).date()
    rows = await session.execute(
        select(Invoice).where(
            Invoice.status == enums.InvoiceStatus.open,
            Invoice.has_active_risk.is_(False),
            Invoice.due_date < today,
        )
    )
    invoices = list(rows.scalars().all())
    created = 0

    for inv in invoices:
        days = (today - inv.due_date).days
        bucket = aging_bucket(days)
        payload = PaymentEventIn(
            merchant_id=inv.merchant_id,
            gateway=enums.Gateway.synthetic,
            event_type=enums.EventType.invoice_overdue,
            amount_paise=inv.amount_paise,
            currency=inv.currency,
            customer_id=inv.customer_id,
            customer_phone=inv.customer_phone,
            customer_email=inv.customer_email,
            payment_method={
                "type": "invoice",
                "invoice_ref": inv.invoice_ref,
                "aging_bucket": bucket,
                "days_overdue": days,
            },
            error_code="invoice_overdue",
            error_description=f"Invoice {inv.invoice_ref} overdue by {days} days ({bucket})",
        )
        pe, risk = await ingest_payment_event(session, payload, inline=True)
        inv.has_active_risk = True
        if risk is not None:
            await orchestrate(session, risk.risk_event_id)
            created += 1
    await session.commit()
    log.info("aging.scan_done", scanned=len(invoices), risks_created=created)
    return {"scanned": len(invoices), "risks_created": created}
