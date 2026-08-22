"""Multi-signal risk scorer.

Pure, deterministic weighting of normalized signals (each 0..1) into a single
risk score (blueprint §9.1). Data fetching lives in ``engine.py``; this module is
kept side-effect-free so it is trivially unit-testable.
"""

from __future__ import annotations

# Signal weights — sum to 1.0.
WEIGHTS: dict[str, float] = {
    "error_code_severity": 0.30,
    "customer_failure_rate_7d": 0.20,
    "bank_failure_rate_1h": 0.15,
    "amount_percentile": 0.15,
    "subscription_health_score": 0.10,
    "fraud_proxy_score": 0.10,
}

# Anomaly layer (IsolationForest) is deferred to P6; when present it adds a boost.
ANOMALY_BOOST = 0.15


def compute_score(
    signal_values: dict[str, float], *, anomaly: bool = False
) -> tuple[float, list[dict]]:
    """Return (risk_score, signals) from normalized signal values.

    Unknown signals are ignored; missing ones default to 0. The score is the
    weighted sum, plus an optional anomaly boost, clamped to [0, 1].
    """
    score = 0.0
    signals: list[dict] = []
    for name, weight in WEIGHTS.items():
        value = max(0.0, min(1.0, float(signal_values.get(name, 0.0))))
        score += weight * value
        signals.append({"signal_type": name, "value": round(value, 4), "weight": weight})

    if anomaly:
        score += ANOMALY_BOOST
        signals.append({"signal_type": "anomaly", "value": 1.0, "weight": ANOMALY_BOOST})

    return round(max(0.0, min(1.0, score)), 4), signals


def amount_percentile(amount_paise: int, reference_paise: int = 5_000_000) -> float:
    """Cheap stand-in for a true percentile: linear ramp to a reference (₹50k)."""
    if amount_paise <= 0:
        return 0.0
    return min(1.0, amount_paise / reference_paise)
