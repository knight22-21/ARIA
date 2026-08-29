"""Inbound webhook endpoints (Path A). Fast-ack; heavy work is enqueued.

Handles the real Razorpay loop:
  - payment.failed      → normalize → detect → agent pipeline
  - payment.captured /
    payment_link.paid   → record the capture and attribute the recovery to the
                          originating risk event (via the aria_risk_event_id we set
                          in the payment link's notes).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.logging import get_logger
from app.execution.outcome import attribute_recovery_for_risk
from app.ingestion.normalize import normalize_razorpay
from app.ingestion.service import ingest_payment_event
from app.integrations.razorpay import verify_webhook_signature
from app.models import enums
from app.schemas.payment import PaymentEventIn

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
log = get_logger(__name__)

_CAPTURE_EVENTS = {"payment.captured", "payment_link.paid", "order.paid"}


def _extract_capture(body: dict[str, Any]) -> dict[str, Any]:
    """Pull amount / customer / notes / id from a capture-style webhook."""
    payload = body.get("payload", {})
    payment = (payload.get("payment") or {}).get("entity", {}) or {}
    link = (payload.get("payment_link") or {}).get("entity", {}) or {}
    notes = payment.get("notes") or link.get("notes") or {}
    amount = payment.get("amount") or link.get("amount_paid") or link.get("amount") or 0
    return {
        "amount_paise": int(amount or 0),
        "email": payment.get("email"),
        "contact": payment.get("contact"),
        "notes": notes,
        "gateway_event_id": payment.get("id") or link.get("id") or body.get("id"),
    }


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    raw = await request.body()

    if not verify_webhook_signature(raw, x_razorpay_signature or ""):
        log.warning("webhook.razorpay.bad_signature")
        raise HTTPException(status_code=403, detail="invalid signature")

    body = await request.json()
    event = body.get("event", "")

    # --- Recovery half: a real payment came in ---
    if event in _CAPTURE_EVENTS:
        cap = _extract_capture(body)
        # Record the captured payment.
        pe, _ = await ingest_payment_event(
            session,
            PaymentEventIn(
                gateway=enums.Gateway.razorpay,
                gateway_event_id=cap["gateway_event_id"],
                event_type=enums.EventType.payment_captured,
                amount_paise=cap["amount_paise"],
                customer_email=cap["email"],
                customer_phone=cap["contact"],
                raw_payload=body,
            ),
            inline=True,
        )
        # Attribute the recovery precisely via the risk-event id we tagged the link with.
        risk_ref = cap["notes"].get("aria_risk_event_id")
        attributed = False
        if risk_ref:
            try:
                attributed = await attribute_recovery_for_risk(
                    session,
                    uuid.UUID(risk_ref),
                    amount_paise=cap["amount_paise"],
                    captured_event_id=pe.event_id if pe else None,
                )
            except (ValueError, TypeError):
                log.warning("webhook.bad_risk_ref", ref=risk_ref)
        log.info("webhook.capture", rzp_event=event, attributed=attributed, risk_ref=risk_ref)
        return {"status": "accepted", "recovery_attributed": attributed}

    # --- Detection half: a failure/at-risk event ---
    payload = normalize_razorpay(body)
    await ingest_payment_event(session, payload, inline=False)
    return {"status": "accepted"}
