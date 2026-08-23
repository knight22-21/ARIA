"""Escalation sub-agent — builds the human-review package."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.structured import StructuredOutputError, run_structured
from app.core.audit import write_audit_event
from app.core.logging import get_logger
from app.models import enums
from app.models.entities import RiskEvent
from app.schemas.agent import DiagnosisResult, EscalationPackage, UrgencyLevel

log = get_logger(__name__)

ACTOR = "escalation-agent@1.0.0"


def _fallback_urgency(amount_paise: int) -> UrgencyLevel:
    if amount_paise > 10_000_000:  # > ₹1L
        return UrgencyLevel.P1
    if amount_paise > 5_000_000:  # > ₹50k
        return UrgencyLevel.P2
    return UrgencyLevel.P3


async def run_escalation(
    session: AsyncSession,
    risk_event: RiskEvent,
    reason: str,
    fired_rules: list[str],
    diagnosis_result: DiagnosisResult | None = None,
) -> EscalationPackage:
    context = {
        "workflow_type": risk_event.workflow_type.value,
        "amount_inr": risk_event.amount_at_risk_paise // 100,
        "escalation_reason": reason,
        "fired_rules": ", ".join(fired_rules) or "none",
        "root_cause_category": (
            diagnosis_result.root_cause_category if diagnosis_result else "unknown"
        ),
        "confidence": diagnosis_result.confidence if diagnosis_result else 0.0,
        "diagnosis_reasoning": (diagnosis_result.reasoning[:800] if diagnosis_result else "n/a"),
    }

    try:
        package, _ = run_structured("escalation", EscalationPackage, context)
    except StructuredOutputError:
        # Deterministic fallback so escalation never fails to produce a package.
        amount_inr = risk_event.amount_at_risk_paise // 100
        package = EscalationPackage(
            summary=f"{risk_event.workflow_type.value} case at risk of ₹{amount_inr}",
            urgency=_fallback_urgency(risk_event.amount_at_risk_paise),
            recommended_action="Manual review required.",
            reason_escalated=reason,
            what_was_tried=[],
        )
        log.warning("escalation.fallback_used", risk_event_id=str(risk_event.risk_event_id))

    risk_event.status = enums.RiskStatus.escalated
    await write_audit_event(
        session,
        event_type="ESCALATION_RAISED",
        actor=ACTOR,
        merchant_id=risk_event.merchant_id,
        entity_type="RiskEvent",
        entity_id=risk_event.risk_event_id,
        payload={
            "urgency": package.urgency.value,
            "reason_escalated": package.reason_escalated,
            "recommended_action": package.recommended_action,
            "summary": package.summary,
            "fired_rules": fired_rules,
        },
    )
    log.info(
        "escalation.raised",
        risk_event_id=str(risk_event.risk_event_id),
        urgency=package.urgency.value,
    )
    return package
