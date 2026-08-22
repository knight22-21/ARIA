"""Error-code taxonomy.

Maps a payment failure code to a severity (0..1) and a coarse decline class.
Severity feeds the ``error_code_severity`` signal (blueprint §9.1). Codes are
normalized to lowercase; both ARIA-canonical codes and common Razorpay/gateway
codes are covered, with a sane default for unknowns.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorClass:
    category: str  # soft_decline | hard_decline | technical | do_not_honour | ...
    severity: float
    recoverable: bool


# Canonical + common gateway codes → classification.
_TAXONOMY: dict[str, ErrorClass] = {
    # Soft declines — recoverable, moderate severity
    "insufficient_funds": ErrorClass("soft_decline", 0.55, True),
    "do_not_honour": ErrorClass("do_not_honour", 0.50, True),
    "do_not_honor": ErrorClass("do_not_honour", 0.50, True),
    "issuer_not_available": ErrorClass("soft_decline", 0.60, True),
    "payment_timeout": ErrorClass("technical", 0.35, True),
    "gateway_timeout": ErrorClass("technical", 0.35, True),
    "bank_declined": ErrorClass("soft_decline", 0.55, True),
    "transaction_limit_exceeded": ErrorClass("soft_decline", 0.45, True),
    # Technical — retry likely to succeed
    "gateway_error": ErrorClass("technical", 0.30, True),
    "network_error": ErrorClass("technical", 0.30, True),
    "server_error": ErrorClass("technical", 0.30, True),
    # Card / mandate lifecycle
    "card_expired": ErrorClass("card_expiry", 0.70, True),
    "expired_card": ErrorClass("card_expiry", 0.70, True),
    "invalid_card": ErrorClass("hard_decline", 0.85, False),
    "card_blocked": ErrorClass("hard_decline", 0.90, False),
    "token_expired": ErrorClass("tokenization", 0.65, True),
    "mandate_expired": ErrorClass("mandate", 0.75, True),
    "mandate_revoked": ErrorClass("hard_decline", 0.88, False),
    # Hard declines — not recoverable by retry
    "stolen_card": ErrorClass("hard_decline", 0.95, False),
    "fraud_suspected": ErrorClass("fraud", 0.95, False),
    "payment_cancelled": ErrorClass("cancelled", 0.20, False),
}

_DEFAULT = ErrorClass("unknown", 0.40, True)


def classify_error(error_code: str | None) -> ErrorClass:
    if not error_code:
        return _DEFAULT
    return _TAXONOMY.get(error_code.strip().lower(), _DEFAULT)
