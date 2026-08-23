"""Diagnostic sub-agent — produces a structured, reasoned root-cause verdict."""

from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.structured import run_structured
from app.core.audit import write_audit_event
from app.core.logging import get_logger
from app.models.entities import Diagnosis, PaymentEvent, RiskEvent
from app.schemas.agent import DiagnosisResult

log = get_logger(__name__)

ACTOR = "diagnostic-agent@1.0.0"


def _signal(signals: list[dict], name: str) -> float:
    for s in signals or []:
        if s.get("signal_type") == name:
            return float(s.get("value", 0.0))
    return 0.0


async def run_diagnostic(
    session: AsyncSession, risk_event: RiskEvent
) -> tuple[DiagnosisResult, Diagnosis]:
    pe = (
        await session.get(PaymentEvent, risk_event.payment_event_id)
        if risk_event.payment_event_id
        else None
    )
    pm = (pe.payment_method if pe else {}) or {}
    signals = risk_event.risk_signals or []

    context = {
        "workflow_type": risk_event.workflow_type.value,
        "amount_inr": risk_event.amount_at_risk_paise // 100,
        "risk_score": risk_event.risk_score,
        "method": pm.get("type", "unknown"),
        "bank": pm.get("bank", "unknown"),
        "bank_failure_rate_1h": round(_signal(signals, "bank_failure_rate_1h"), 3),
        "customer_failure_rate_7d": round(_signal(signals, "customer_failure_rate_7d"), 3),
        "error_code": (pe.error_code if pe else None) or "none",
        "error_description": (pe.error_description if pe else None) or "none",
        "risk_signals": json.dumps(signals),
    }

    result, resp = run_structured("diagnostic", DiagnosisResult, context)

    # Prefer the JSON `reasoning` field (a clean, purpose-written analysis) for
    # display; fall back to the provider's raw chain-of-thought if it's empty.
    reasoning_chain = result.reasoning.strip() or resp.reasoning

    diagnosis = Diagnosis(
        risk_event_id=risk_event.risk_event_id,
        root_cause_category=result.root_cause_category[:64],
        confidence=result.confidence,
        reasoning_chain=reasoning_chain,
        evidence_signals={"evidence": result.evidence, "detector_signals": signals},
        recommended_intervention_class=result.recommended_intervention_class[:64],
        urgency_score=result.urgency_score,
        llm_model=f"{resp.provider}:{resp.model}",
        llm_prompt_version="1.0.0",
        input_token_count=resp.input_tokens,
        output_token_count=resp.output_tokens,
    )
    session.add(diagnosis)
    await session.flush()

    await write_audit_event(
        session,
        event_type="DIAGNOSIS_PRODUCED",
        actor=ACTOR,
        merchant_id=risk_event.merchant_id,
        entity_type="Diagnosis",
        entity_id=diagnosis.diagnosis_id,
        payload={
            "root_cause_category": result.root_cause_category,
            "confidence": result.confidence,
            "recommended_intervention_class": result.recommended_intervention_class,
            "urgency_score": result.urgency_score,
            "reasoning_chain": reasoning_chain,
            "llm_model": diagnosis.llm_model,
            "prompt_version": "1.0.0",
        },
    )
    log.info(
        "diagnostic.done",
        risk_event_id=str(risk_event.risk_event_id),
        root_cause=result.root_cause_category,
        confidence=result.confidence,
    )
    return result, diagnosis
