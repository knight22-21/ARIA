"""Tests for PII encryption and webhook signature verification."""

import hashlib
import hmac

from app.core import crypto
from app.integrations.razorpay import verify_webhook_signature


def test_encrypt_roundtrip_with_key(monkeypatch):
    key = b"0123456789abcdef0123456789abcdef"  # 32 bytes
    monkeypatch.setattr(crypto, "_KEY", key)

    ct = crypto.encrypt_field("+919812345670")
    assert ct is not None
    assert ct.startswith(crypto._PREFIX)  # marked encrypted
    assert ct != "+919812345670"
    assert crypto.decrypt_field(ct) == "+919812345670"

    # Idempotent: encrypting an already-encrypted value is a no-op.
    assert crypto.encrypt_field(ct) == ct


def test_encrypt_passthrough_without_key(monkeypatch):
    monkeypatch.setattr(crypto, "_KEY", None)
    assert crypto.encrypt_field("plain") == "plain"
    assert crypto.decrypt_field("plain") == "plain"
    assert crypto.encrypt_field(None) is None


def test_razorpay_signature_valid_and_invalid():
    secret = "whsec_test_123"
    body = b'{"event":"payment.failed"}'
    good = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    assert verify_webhook_signature(body, good, secret) is True
    assert verify_webhook_signature(body, "deadbeef", secret) is False
    assert verify_webhook_signature(body, "", secret) is False
    assert verify_webhook_signature(body, good, "") is False  # no secret configured
