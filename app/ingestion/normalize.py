"""Normalize gateway webhook payloads → the canonical ``PaymentEventIn``.

Only Razorpay is implemented for this build; the schema stays gateway-agnostic so
Stripe/Cashfree normalizers could slot in later without touching downstream code.
"""

from __future__ import annotations

from typing import Any

from app.models import enums
from app.schemas.payment import PaymentEventIn

# Razorpay event name → our EventType.
_RZP_EVENT_MAP: dict[str, enums.EventType] = {
    "payment.failed": enums.EventType.payment_failed,
    "payment.captured": enums.EventType.payment_captured,
    "subscription.charged": enums.EventType.subscription_charged,
    "subscription.halted": enums.EventType.subscription_halted,
    "mandate.confirmed": enums.EventType.mandate_confirmed,
    "mandate.rejected": enums.EventType.mandate_rejected,
    "mandate.debited": enums.EventType.mandate_debited,
}


def normalize_razorpay(body: dict[str, Any]) -> PaymentEventIn:
    """Map a Razorpay webhook body to PaymentEventIn.

    Razorpay wraps the entity under ``payload.<entity>.entity``; we read the
    payment entity when present and fall back gracefully.
    """
    event_name = body.get("event", "")
    event_type = _RZP_EVENT_MAP.get(event_name, enums.EventType.payment_failed)

    payload = body.get("payload", {})
    payment = (payload.get("payment") or {}).get("entity", {}) or {}

    method = payment.get("method")
    pm: dict[str, Any] = {"type": method} if method else {}
    if payment.get("card"):
        card = payment["card"]
        pm["card_last4"] = card.get("last4")
        pm["bank"] = card.get("issuer") or card.get("network")
    if payment.get("bank"):
        pm["bank"] = payment["bank"]
    if payment.get("vpa"):
        pm["vpa"] = payment["vpa"]

    return PaymentEventIn(
        gateway=enums.Gateway.razorpay,
        gateway_event_id=payment.get("id") or body.get("id"),
        event_type=event_type,
        amount_paise=int(payment.get("amount", 0) or 0),
        currency=payment.get("currency", "INR"),
        customer_id=payment.get("customer_id") or payment.get("email"),
        customer_phone=payment.get("contact"),
        customer_email=payment.get("email"),
        payment_method=pm,
        error_code=payment.get("error_reason") or payment.get("error_code"),
        error_description=payment.get("error_description"),
        raw_payload=body,
    )
