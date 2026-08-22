"""Unit tests for the pure detection logic (no DB/Redis)."""

from app.detection import scorer
from app.detection.classifier import classify_workflow
from app.detection.taxonomy import classify_error
from app.models import enums


def test_taxonomy_known_and_unknown():
    assert classify_error("insufficient_funds").category == "soft_decline"
    assert classify_error("INSUFFICIENT_FUNDS").recoverable is True  # case-insensitive
    assert classify_error("fraud_suspected").severity >= 0.9
    unknown = classify_error("some_new_code")
    assert unknown.category == "unknown"
    assert 0.0 <= unknown.severity <= 1.0


def test_weights_sum_to_one():
    assert abs(sum(scorer.WEIGHTS.values()) - 1.0) < 1e-9


def test_compute_score_is_weighted_and_clamped():
    # All signals maxed → score 1.0 (weights sum to 1).
    score, signals = scorer.compute_score(dict.fromkeys(scorer.WEIGHTS, 1.0))
    assert score == 1.0
    assert len(signals) == len(scorer.WEIGHTS)

    # All zero → 0.0
    score0, _ = scorer.compute_score({})
    assert score0 == 0.0

    # Single signal reflects its weight.
    s, _ = scorer.compute_score({"error_code_severity": 1.0})
    assert abs(s - scorer.WEIGHTS["error_code_severity"]) < 1e-9


def test_anomaly_boost_clamps():
    score, signals = scorer.compute_score(dict.fromkeys(scorer.WEIGHTS, 1.0), anomaly=True)
    assert score == 1.0  # 1.0 + boost, clamped
    assert any(s["signal_type"] == "anomaly" for s in signals)


def test_amount_percentile():
    assert scorer.amount_percentile(0) == 0.0
    assert scorer.amount_percentile(5_000_000) == 1.0
    assert scorer.amount_percentile(10_000_000) == 1.0  # clamped
    assert 0.0 < scorer.amount_percentile(2_500_000) < 1.0


def test_workflow_classifier():
    cases = {
        enums.EventType.payment_failed: enums.WorkflowType.payment_degradation,
        enums.EventType.subscription_halted: enums.WorkflowType.subscription_failure,
        enums.EventType.mandate_rejected: enums.WorkflowType.mandate_retry,
        enums.EventType.invoice_overdue: enums.WorkflowType.b2b_receivable,
        enums.EventType.checkout_abandoned: enums.WorkflowType.checkout_abandonment,
    }
    for event_type, expected in cases.items():
        assert classify_workflow(event_type) == expected
