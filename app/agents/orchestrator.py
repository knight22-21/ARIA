"""Orchestrator — the agent state machine.

Nodes: CheckPolicy → RunDiagnosis → SelectIntervention → (Execute | Escalate).
Implemented as an explicit async pipeline (not LangGraph) for reliability and to
avoid async-session friction; the node structure maps 1:1 to the graph in the
blueprint and every transition is written to the audit ledger.

Guarantees:
  - Deterministic policy gate runs first (DNC/fraud/caps) — never skipped.
  - Diagnosis confidence < 0.6 auto-escalates (blueprint §10.3).
  - LLM failure falls back to human escalation (safe), logged in the ledger.
  - A Redis lock on risk_event_id prevents double-processing.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.diagnostic import run_diagnostic
from app.agents.escalation import run_escalation
from app.agents.intervention import run_intervention
from app.agents.llm import LLMError
from app.agents.policy import build_policy_context, evaluate_policy
from app.agents.structured import StructuredOutputError
from app.core.audit import write_audit_event
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.models import enums
from app.models.entities import Merchant, RiskEvent
from app.schemas.agent import OrchestratorState

log = get_logger(__name__)

ACTOR = "orchestrator@1.0.0"
CONFIDENCE_ESCALATION_THRESHOLD = 0.60
_LOCK_TTL = 600  # seconds — longer than max processing time


async def orchestrate(session: AsyncSession, risk_event_id: uuid.UUID) -> OrchestratorState | None:
    """Drive one RiskEvent through the agent pipeline. Idempotent + lock-guarded."""
    r = get_redis()
    lock_key = f"aria:lock:orch:{risk_event_id}"
    if not await r.set(lock_key, "1", nx=True, ex=_LOCK_TTL):
        log.info("orchestrate.locked_skip", risk_event_id=str(risk_event_id))
        return None

    try:
        risk = await session.get(RiskEvent, risk_event_id)
        if risk is None:
            log.warning("orchestrate.missing", risk_event_id=str(risk_event_id))
            return None
        if risk.status != enums.RiskStatus.detected:
            log.info("orchestrate.already_processed", status=risk.status.value)
            return None

        merchant = await session.get(Merchant, risk.merchant_id)
        config = (merchant.config if merchant else {}) or {}

        state = OrchestratorState(
            risk_event_id=risk.risk_event_id,
            merchant_id=risk.merchant_id,
            workflow_type=risk.workflow_type,
            amount_at_risk_paise=risk.amount_at_risk_paise,
        )

        # ---- Node: CheckPolicy ----
        ctx = await build_policy_context(session, risk, config)
        decision = evaluate_policy(ctx)
        state.policy = decision
        await write_audit_event(
            session,
            event_type="POLICY_CHECKED",
            actor=ACTOR,
            merchant_id=risk.merchant_id,
            entity_type="RiskEvent",
            entity_id=risk.risk_event_id,
            payload={
                "action": decision.action,
                "fired_rules": decision.fired_rules,
                "reason": decision.reason,
                "is_dnc": ctx.is_dnc,
                "fraud_score": ctx.fraud_score,
                "amount_paise": ctx.amount_paise,
            },
        )

        if decision.action == "suppress":
            risk.status = enums.RiskStatus.suppressed
            await write_audit_event(
                session, event_type="STOPPING_RULE_FIRED", actor=ACTOR,
                merchant_id=risk.merchant_id, entity_type="RiskEvent",
                entity_id=risk.risk_event_id,
                payload={"fired_rules": decision.fired_rules, "reason": decision.reason},
            )
            state.outcome = "suppressed"
            return await _finish(session, risk, state)

        if decision.action == "escalate":
            pkg = await run_escalation(session, risk, decision.reason, decision.fired_rules)
            state.escalation = pkg
            state.outcome = "escalated"
            return await _finish(session, risk, state)

        # ---- Node: RunDiagnosis ----
        try:
            diag_result, diag_row = await run_diagnostic(session, risk)
        except (StructuredOutputError, LLMError) as exc:
            pkg = await run_escalation(session, risk, f"diagnosis_failed: {exc}", [])
            state.escalation = pkg
            state.outcome = "escalated"
            return await _finish(session, risk, state)

        state.diagnosis = diag_result
        state.diagnosis_id = diag_row.diagnosis_id

        if diag_result.confidence < CONFIDENCE_ESCALATION_THRESHOLD:
            pkg = await run_escalation(
                session, risk, "diagnosis_confidence_below_threshold", [], diag_result
            )
            state.escalation = pkg
            state.outcome = "escalated"
            return await _finish(session, risk, state)

        # ---- Node: SelectIntervention ----
        try:
            interv_result, plan = await run_intervention(
                session, risk, diag_row, diag_result, config
            )
        except (StructuredOutputError, LLMError) as exc:
            pkg = await run_escalation(
                session, risk, f"intervention_failed: {exc}", [], diag_result
            )
            state.escalation = pkg
            state.outcome = "escalated"
            return await _finish(session, risk, state)

        state.intervention = interv_result
        state.plan_id = plan.plan_id
        risk.status = enums.RiskStatus.in_progress

        # ---- Node: Execute ----
        from app.execution.dispatcher import execute_plan

        await execute_plan(session, plan.plan_id)
        # Re-attach risk to this session (execute_plan committed) before finishing.
        risk = await session.get(RiskEvent, risk.risk_event_id)
        state.outcome = "proceeded"
        return await _finish(session, risk, state)
    finally:
        await r.delete(lock_key)


async def _finish(
    session: AsyncSession, risk: RiskEvent, state: OrchestratorState
) -> OrchestratorState:
    """Write the terminal AGENT_DECISION snapshot and commit."""
    await write_audit_event(
        session,
        event_type="AGENT_DECISION",
        actor=ACTOR,
        merchant_id=risk.merchant_id,
        entity_type="RiskEvent",
        entity_id=risk.risk_event_id,
        payload={"outcome": state.outcome, "state": state.model_dump(mode="json")},
    )
    await session.commit()
    log.info("orchestrate.done", risk_event_id=str(risk.risk_event_id), outcome=state.outcome)
    return state
