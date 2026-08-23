"""Stopping-Rules engine + policy enforcement (blueprint §12.1, §10.4).

Deterministic, LLM-free, and the circuit breaker of the system: it runs before any
agent reasoning. The pure predicate (``evaluate_policy``) is separated from the
async data-gathering (``build_policy_context``) so the rule logic is unit-testable.

Outcomes:
  proceed   — no rule blocks autonomous action
  suppress  — do not contact (DNC / dispute / contact & retry caps)
  escalate  — hand to a human (fraud hold / amount over ceiling)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import hash_identifier
from app.models import enums
from app.models.entities import (
    DNCEntry,
    InterventionPlan,
    Outbox,
    PaymentEvent,
    RiskEvent,
)
from app.schemas.agent import PolicyDecision

# Hard global limits (apply to every merchant).
GLOBAL_MAX_RETRIES = 5
GLOBAL_MAX_CONTACTS_24H = 3
FRAUD_HOLD_THRESHOLD = 0.85


@dataclass
class PolicyContext:
    amount_paise: int
    is_dnc: bool = False
    fraud_score: float = 0.0
    has_active_dispute: bool = False
    retries_for_payment: int = 0
    contacts_24h: int = 0
    contacts_7d: int = 0
    # Merchant config
    auto_action_ceiling_paise: int = 5_000_000
    max_contacts_per_customer_7d: int = 6
    max_retries_per_payment: int = 3
    fired: list[str] = field(default_factory=list)


def evaluate_policy(ctx: PolicyContext) -> PolicyDecision:
    """Pure rule evaluation. Global rules first, then merchant rules.

    suppress takes precedence over escalate (more conservative — don't contact).
    """
    suppress: list[str] = []
    escalate: list[str] = []

    # --- Global rules ---
    if ctx.is_dnc:
        suppress.append("DNC_CHECK")
    if ctx.has_active_dispute:
        suppress.append("LEGAL_DISPUTE")
    if ctx.retries_for_payment >= GLOBAL_MAX_RETRIES:
        suppress.append("HARDCODED_MAX_RETRIES")
    if ctx.contacts_24h >= GLOBAL_MAX_CONTACTS_24H:
        suppress.append("HARDCODED_MAX_CONTACTS_24H")
    if ctx.fraud_score > FRAUD_HOLD_THRESHOLD:
        escalate.append("FRAUD_HOLD")

    # --- Merchant-configurable rules ---
    if ctx.contacts_7d >= ctx.max_contacts_per_customer_7d:
        suppress.append("MAX_CONTACTS_PER_CUSTOMER_7D")
    if ctx.retries_for_payment >= ctx.max_retries_per_payment:
        suppress.append("MAX_RETRIES_PER_PAYMENT")
    if ctx.amount_paise > ctx.auto_action_ceiling_paise:
        escalate.append("AMOUNT_OVER_CEILING")

    fired = suppress + escalate
    if suppress:
        return PolicyDecision(
            allowed=False, action="suppress", fired_rules=fired,
            reason=f"stopping rule(s) fired: {', '.join(suppress)}",
        )
    if escalate:
        return PolicyDecision(
            allowed=False, action="escalate", fired_rules=fired,
            reason=f"policy requires human review: {', '.join(escalate)}",
        )
    return PolicyDecision(allowed=True, action="proceed", fired_rules=[], reason="no rules fired")


def _fraud_from_signals(signals: list[dict]) -> float:
    for s in signals or []:
        if s.get("signal_type") == "fraud_proxy_score":
            return float(s.get("value", 0.0))
    return 0.0


async def build_policy_context(
    session: AsyncSession, risk_event: RiskEvent, merchant_config: dict
) -> PolicyContext:
    """Gather the facts the rule engine needs from Postgres."""
    from datetime import UTC, datetime, timedelta

    pe = (
        await session.get(PaymentEvent, risk_event.payment_event_id)
        if risk_event.payment_event_id
        else None
    )
    customer_id = pe.customer_id if pe else None
    now = datetime.now(UTC)

    # DNC: match hashed phone or email against this merchant's DNC list.
    is_dnc = False
    if pe:
        identifiers = [
            h
            for h in (hash_identifier(pe.customer_phone), hash_identifier(pe.customer_email))
            if h
        ]
        if identifiers:
            hit = await session.scalar(
                select(func.count())
                .select_from(DNCEntry)
                .where(
                    DNCEntry.merchant_id == risk_event.merchant_id,
                    DNCEntry.customer_identifier.in_(identifiers),
                )
            )
            is_dnc = bool(hit)

    # Retries already attempted for this risk event.
    retries = await session.scalar(
        select(func.count())
        .select_from(InterventionPlan)
        .where(
            InterventionPlan.risk_event_id == risk_event.risk_event_id,
            InterventionPlan.action_type == enums.ActionType.retry_payment,
        )
    ) or 0

    # Contact counts for this customer over 24h / 7d (join outbox → plan → risk → payment).
    contacts_24h = contacts_7d = 0
    if customer_id:
        base = (
            select(func.count())
            .select_from(Outbox)
            .join(InterventionPlan, Outbox.plan_id == InterventionPlan.plan_id)
            .join(RiskEvent, InterventionPlan.risk_event_id == RiskEvent.risk_event_id)
            .join(PaymentEvent, RiskEvent.payment_event_id == PaymentEvent.event_id)
            .where(PaymentEvent.customer_id == customer_id)
        )
        contacts_24h = (
            await session.scalar(base.where(Outbox.created_at >= now - timedelta(hours=24))) or 0
        )
        contacts_7d = (
            await session.scalar(base.where(Outbox.created_at >= now - timedelta(days=7))) or 0
        )

    thresholds = merchant_config.get("thresholds", {})
    stopping = merchant_config.get("stopping_rules", {})

    return PolicyContext(
        amount_paise=risk_event.amount_at_risk_paise,
        is_dnc=is_dnc,
        fraud_score=_fraud_from_signals(risk_event.risk_signals),
        has_active_dispute=False,  # dispute/chargeback feed not modeled in this build
        retries_for_payment=retries,
        contacts_24h=contacts_24h,
        contacts_7d=contacts_7d,
        auto_action_ceiling_paise=thresholds.get("auto_action_amount_ceiling_paise", 5_000_000),
        max_contacts_per_customer_7d=stopping.get("max_contacts_per_customer_7d", 6),
        max_retries_per_payment=stopping.get("max_retries_per_payment", 3),
    )
