"""Tests for the execution layer registry + P&L helper (pure parts)."""

from app.analytics.pnl import _rupees
from app.execution.dispatcher import _REGISTRY
from app.models import enums


def test_every_action_has_an_executor():
    """No action in the bounded space may be unhandled at dispatch time."""
    missing = [a for a in enums.ActionType if a not in _REGISTRY]
    assert not missing, f"actions without executor: {missing}"


def test_message_and_retry_costs():
    from app.execution.executors import MessageExecutor, RetryPaymentExecutor
    from app.models.entities import InterventionPlan

    plan = InterventionPlan(
        risk_event_id=None, action_type=enums.ActionType.send_payment_link, estimated_cost_paise=0
    )
    assert MessageExecutor().estimate_cost(plan) == 150
    assert RetryPaymentExecutor().estimate_cost(plan) == 0


def test_rupees_conversion():
    assert _rupees(1_240_000) == 12400.0
    assert _rupees(0) == 0.0
    assert _rupees(None) == 0.0
