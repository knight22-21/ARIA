"""Razorpay webhook signature verification + payload normalization helpers.

Only the pieces needed for ingestion live here. Outbound calls (retry/payment
link) arrive in Phase 3.
"""

from __future__ import annotations

import hashlib
import hmac

from app.core.config import settings


def verify_webhook_signature(raw_body: bytes, signature: str, secret: str | None = None) -> bool:
    """Verify Razorpay's ``X-Razorpay-Signature`` (HMAC-SHA256 of the raw body).

    Returns True when valid. Uses a constant-time comparison.
    """
    secret = secret or settings.razorpay_webhook_secret
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
