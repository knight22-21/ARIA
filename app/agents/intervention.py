"""Intervention Selector sub-agent — picks a bounded action + generates content."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.hinglish import build_message_guidance
from app.agents.structured import run_structured
from app.core.audit import write_audit_event
from app.core.logging import get_logger
from app.models import enums
from app.models.entities import Diagnosis, InterventionPlan, PaymentEvent, RiskEvent
from app.schemas.agent import DiagnosisResult, InterventionResult

log = get_logger(__name__)

ACTOR = "intervention-selector@1.0.0"

# Rough per-action cost in paise (message send ≈ ₹1.5; retries free; IVR pricier).
_ACTION_COST: dict[enums.ActionType, int] = {
    enums.ActionType.retry_payment: 0,
    enums.ActionType.schedule_retry: 0,
    enums.ActionType.suppress: 0,
    enums.ActionType.generate_voice_script: 0,
    enums.ActionType.escalate_human: 0,
    enums.ActionType.trigger_ivr_call: 500,
}
_DEFAULT_MSG_COST = 150


def _estimate_cost(action: enums.ActionType) -> int:
    return _ACTION_COST.get(action, _DEFAULT_MSG_COST)


async def run_intervention(
    session: AsyncSession,
    risk_event: RiskEvent,
    diagnosis: Diagnosis,
    diagnosis_result: DiagnosisResult,
    merchant_config: dict,
    *,
    human_approved: bool = False,
) -> tuple[InterventionResult, InterventionPlan]:
    channels = merchant_config.get("channels", {})
    allowed_channels = [
        c for c, key in (
            ("whatsapp", "whatsapp_enabled"),
            ("sms", "sms_enabled"),
            ("email", "email_enabled"),
            ("ivr", "voice_enabled"),
        ) if channels.get(key, False)
    ]
    thresholds = merchant_config.get("thresholds", {})
    ceiling_inr = thresholds.get("auto_action_amount_ceiling_paise", 5_000_000) // 100
    language = "hinglish" if merchant_config.get("hinglish_mode") else "english"

    # B2B/enterprise cases use a more formal tone; retail is casual.
    tier = (
        "enterprise"
        if risk_event.workflow_type == enums.WorkflowType.b2b_receivable
        else "retail"
    )

    # Aging bucket (B2B) is stashed on the payment event's method dict by the scanner.
    pe = (
        await session.get(PaymentEvent, risk_event.payment_event_id)
        if risk_event.payment_event_id
        else None
    )
    aging_bucket = ((pe.payment_method if pe else {}) or {}).get("aging_bucket", "")

    context = {
        "root_cause_category": diagnosis_result.root_cause_category,
        "confidence": diagnosis_result.confidence,
        "recommended_intervention_class": diagnosis_result.recommended_intervention_class,
        "urgency_score": diagnosis_result.urgency_score,
        "diagnosis_reasoning": diagnosis_result.reasoning[:800],
        "workflow_type": risk_event.workflow_type.value,
        "amount_inr": risk_event.amount_at_risk_paise // 100,
        "language": language,
        "allowed_channels": ", ".join(allowed_channels) or "none",
        "auto_action_ceiling_inr": ceiling_inr,
        "emi_enabled": merchant_config.get("discount_offer_enabled", True),
        "discount_enabled": merchant_config.get("discount_offer_enabled", True),
        "aging_bucket": aging_bucket,
        "human_approved": human_approved,
        "hinglish_guidance": build_message_guidance(language, tier),
    }

    result, resp = run_structured("intervention_selector", InterventionResult, context)

    # Channel guardrail: if a disabled channel was chosen for a messaging action,
    # fall back to the first allowed channel (or none for internal actions).
    channel = result.channel
    needs_correction = (
        channel is not None
        and channel != enums.Channel.internal_retry
        and channel.value not in allowed_channels
    )
    if needs_correction:
        corrected = enums.Channel(allowed_channels[0]) if allowed_channels else None
        log.warning(
            "intervention.channel_corrected",
            chosen=channel.value if channel else None,
            corrected=corrected.value if corrected else None,
        )
        channel = corrected

    scheduled_at = datetime.now(UTC) + timedelta(hours=max(0.0, result.scheduled_offset_hours))

    plan = InterventionPlan(
        diagnosis_id=diagnosis.diagnosis_id,
        risk_event_id=risk_event.risk_event_id,
        action_type=result.action_type,
        channel=channel,
        scheduled_at=scheduled_at,
        message_content=result.message_content,
        attribution_window_hours=result.attribution_window_hours,
        estimated_cost_paise=_estimate_cost(result.action_type),
        status=enums.PlanStatus.planned,
    )
    session.add(plan)
    await session.flush()

    await write_audit_event(
        session,
        event_type="INTERVENTION_PLANNED",
        actor=ACTOR,
        merchant_id=risk_event.merchant_id,
        entity_type="InterventionPlan",
        entity_id=plan.plan_id,
        correlation_id=risk_event.risk_event_id,
        payload={
            "action_type": result.action_type.value,
            "channel": channel.value if channel else None,
            "scheduled_at": scheduled_at.isoformat(),
            "attribution_window_hours": result.attribution_window_hours,
            "estimated_cost_paise": plan.estimated_cost_paise,
            "reasoning": result.reasoning,
            "has_message": bool(result.message_content),
        },
    )
    log.info(
        "intervention.planned",
        risk_event_id=str(risk_event.risk_event_id),
        action=result.action_type.value,
        channel=channel.value if channel else None,
    )
    return result, plan
