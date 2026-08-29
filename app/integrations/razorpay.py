"""Razorpay integration — webhook verification + outbound Payment Links API."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

_API_BASE = "https://api.razorpay.com/v1"


def verify_webhook_signature(raw_body: bytes, signature: str, secret: str | None = None) -> bool:
    """Verify Razorpay's ``X-Razorpay-Signature`` (HMAC-SHA256 of the raw body).

    Returns True when valid. Uses a constant-time comparison.
    """
    secret = secret or settings.razorpay_webhook_secret
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def is_configured() -> bool:
    return bool(settings.razorpay_key_id and settings.razorpay_key_secret)


async def create_payment_link(
    *,
    amount_paise: int,
    description: str,
    reference_id: str,
    customer_name: str | None = None,
    customer_email: str | None = None,
    customer_contact: str | None = None,
    notes: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Create a real Razorpay Payment Link (test mode). Returns {id, short_url} or None.

    ``notes`` travels back on the payment.captured / payment_link.paid webhook, which is
    how we attribute the recovery precisely to the originating risk event.
    """
    if not is_configured():
        return None

    body: dict[str, Any] = {
        "amount": amount_paise,
        "currency": "INR",
        "accept_partial": False,
        "description": description[:255],
        "reference_id": reference_id[:40],
        "notify": {"sms": False, "email": False},
        "reminder_enable": False,
        "notes": notes or {},
    }
    customer: dict[str, str] = {}
    if customer_name:
        customer["name"] = customer_name[:120]
    if customer_email:
        customer["email"] = customer_email
    if customer_contact:
        customer["contact"] = customer_contact
    if customer:
        body["customer"] = customer

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{_API_BASE}/payment_links",
                json=body,
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
            )
        if resp.status_code >= 300:
            log.warning("razorpay.link_failed", status=resp.status_code, body=resp.text[:300])
            return None
        data = resp.json()
        return {"id": data.get("id"), "short_url": data.get("short_url")}
    except Exception as exc:  # noqa: BLE001 — never break the pipeline on a link failure
        log.warning("razorpay.link_error", error=str(exc))
        return None
