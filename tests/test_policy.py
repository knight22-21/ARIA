"""Unit tests for the deterministic stopping-rules engine."""

from app.agents.policy import PolicyContext, evaluate_policy


def _ctx(**kw) -> PolicyContext:
    base = dict(amount_paise=100_000)
    base.update(kw)
    return PolicyContext(**base)


def test_clean_case_proceeds():
    d = evaluate_policy(_ctx())
    assert d.allowed is True
    assert d.action == "proceed"
    assert d.fired_rules == []


def test_dnc_suppresses():
    d = evaluate_policy(_ctx(is_dnc=True))
    assert d.action == "suppress"
    assert "DNC_CHECK" in d.fired_rules


def test_fraud_escalates():
    d = evaluate_policy(_ctx(fraud_score=0.9))
    assert d.action == "escalate"
    assert "FRAUD_HOLD" in d.fired_rules


def test_amount_over_ceiling_escalates():
    d = evaluate_policy(_ctx(amount_paise=6_000_000, auto_action_ceiling_paise=5_000_000))
    assert d.action == "escalate"
    assert "AMOUNT_OVER_CEILING" in d.fired_rules


def test_suppress_beats_escalate():
    # DNC (suppress) + amount over ceiling (escalate) → suppress wins (don't contact).
    d = evaluate_policy(
        _ctx(is_dnc=True, amount_paise=9_000_000, auto_action_ceiling_paise=5_000_000)
    )
    assert d.action == "suppress"
    assert "DNC_CHECK" in d.fired_rules


def test_contact_and_retry_caps():
    assert evaluate_policy(_ctx(contacts_24h=3)).action == "suppress"
    assert evaluate_policy(_ctx(contacts_7d=6, max_contacts_per_customer_7d=6)).action == "suppress"
    assert evaluate_policy(_ctx(retries_for_payment=5)).action == "suppress"
    assert (
        evaluate_policy(_ctx(retries_for_payment=3, max_retries_per_payment=3)).action
        == "suppress"
    )
