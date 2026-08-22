"""Tests for Razorpay webhook normalization + scenario building."""

from app.ingestion.normalize import normalize_razorpay
from app.ingestion.scenarios import build_scenario, scenario_names
from app.models import enums


def test_normalize_razorpay_payment_failed():
    body = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_ABC123",
                    "amount": 1240000,
                    "currency": "INR",
                    "email": "asha@example.com",
                    "contact": "+919812345670",
                    "method": "card",
                    "card": {"last4": "4321", "issuer": "HDFC"},
                    "error_reason": "insufficient_funds",
                    "error_description": "Insufficient balance",
                }
            }
        },
    }
    ev = normalize_razorpay(body)
    assert ev.gateway == enums.Gateway.razorpay
    assert ev.event_type == enums.EventType.payment_failed
    assert ev.gateway_event_id == "pay_ABC123"
    assert ev.amount_paise == 1240000
    assert ev.payment_method["bank"] == "HDFC"
    assert ev.error_code == "insufficient_funds"
    assert ev.raw_payload == body


def test_all_scenarios_build():
    names = scenario_names()
    assert "hdfc_soft_decline" in names
    for name in names:
        ev = build_scenario(name)
        assert ev.gateway == enums.Gateway.synthetic
        assert ev.event_type in set(enums.EventType)
