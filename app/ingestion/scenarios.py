"""Synthetic scenario library for the injector (Path B).

Each scenario returns a ``PaymentEventIn``. Used by ``scripts/inject.py`` and the
``/dev/inject`` endpoint to exercise the pipeline without a live gateway.
"""

from __future__ import annotations

from app.models import enums
from app.schemas.payment import PaymentEventIn

_SCENARIOS: dict[str, dict] = {
    "hdfc_soft_decline": {
        "event_type": enums.EventType.payment_failed,
        "amount_paise": 1_240_000,  # ₹12,400
        "customer_id": "cust_hdfc_001",
        "customer_phone": "+919812345670",
        "customer_email": "asha.rao@example.com",
        "payment_method": {"type": "card", "card_last4": "4321", "bank": "HDFC"},
        "error_code": "insufficient_funds",
        "error_description": "Insufficient balance in account",
    },
    "icici_do_not_honour": {
        "event_type": enums.EventType.payment_failed,
        "amount_paise": 340_000,  # ₹3,400
        "customer_id": "cust_icici_007",
        "customer_phone": "+919812345671",
        "customer_email": "vikram.singh@example.com",
        "payment_method": {"type": "card", "card_last4": "9087", "bank": "ICICI"},
        "error_code": "do_not_honour",
        "error_description": "Issuer declined the transaction",
    },
    "subscription_fail_hdfc": {
        "event_type": enums.EventType.subscription_halted,
        "amount_paise": 79_900,  # ₹799 SaaS sub
        "customer_id": "cust_sub_042",
        "customer_phone": "+919812345672",
        "customer_email": "team@acmestartup.example.com",
        "payment_method": {"type": "upi_autopay", "bank": "HDFC", "vpa": "acme@okhdfcbank"},
        "error_code": "insufficient_funds",
        "error_description": "Autopay debit failed — insufficient funds",
    },
    "mandate_reject": {
        "event_type": enums.EventType.mandate_rejected,
        "amount_paise": 250_000,  # ₹2,500
        "customer_id": "cust_mandate_019",
        "customer_phone": "+919812345673",
        "customer_email": "rahul.mehta@example.com",
        "payment_method": {"type": "nach", "bank": "SBI"},
        "error_code": "mandate_expired",
        "error_description": "NACH mandate has expired",
    },
    "checkout_abandon": {
        "event_type": enums.EventType.checkout_abandoned,
        "amount_paise": 890_000,  # ₹8,900 cart
        "customer_id": "cust_checkout_113",
        "customer_phone": "+919812345674",
        "customer_email": "priya.nair@example.com",
        "payment_method": {"type": "unknown"},
        "error_code": None,
        "error_description": "Checkout session expired without payment",
    },
    "b2b_invoice_small": {
        "event_type": enums.EventType.invoice_overdue,
        "amount_paise": 35_000_00,  # ₹35,000 — under the ₹50k ceiling, proceeds autonomously
        "customer_id": "cust_b2b_bright_014",
        "customer_phone": "+919812345680",
        "customer_email": "ap@brightretail.example.com",
        "payment_method": {"type": "invoice", "aging_bucket": "31-60", "days_overdue": 44},
        "error_code": "invoice_overdue",
        "error_description": "Invoice INV-0042 overdue by 44 days (31-60)",
    },
    "b2b_invoice_overdue": {
        "event_type": enums.EventType.invoice_overdue,
        "amount_paise": 2_30_00_000,  # ₹2.3L
        "customer_id": "cust_b2b_enterprise_003",
        "customer_phone": "+919812345675",
        "customer_email": "ap@bigcorp.example.com",
        "payment_method": {"type": "invoice"},
        "error_code": None,
        "error_description": "Invoice 45 days overdue",
    },
    "technical_gateway": {
        "event_type": enums.EventType.payment_failed,
        "amount_paise": 156_000,  # ₹1,560
        "customer_id": "cust_tech_088",
        "customer_phone": "+919812345676",
        "customer_email": "sana.k@example.com",
        "payment_method": {"type": "card", "card_last4": "1102", "bank": "AXIS"},
        "error_code": "gateway_error",
        "error_description": "Gateway timeout during authorization",
    },
    "fraud_hard_decline": {
        "event_type": enums.EventType.payment_failed,
        "amount_paise": 4_500_000,  # ₹45,000
        "customer_id": "cust_fraud_555",
        "customer_phone": "+919812345677",
        "customer_email": "unknown@example.com",
        "payment_method": {"type": "card", "card_last4": "0000", "bank": "UNKNOWN"},
        "error_code": "fraud_suspected",
        "error_description": "Transaction flagged by fraud engine",
    },
}


def scenario_names() -> list[str]:
    return sorted(_SCENARIOS)


def build_scenario(name: str) -> PaymentEventIn:
    if name not in _SCENARIOS:
        raise KeyError(f"unknown scenario '{name}'. available: {', '.join(scenario_names())}")
    return PaymentEventIn(gateway=enums.Gateway.synthetic, **_SCENARIOS[name])
