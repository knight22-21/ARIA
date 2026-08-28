"""Execution dispatcher — routes an InterventionPlan to its executor.

Applies the frequency cap, runs the executor, updates plan status/executed_at, and
writes an ACTION_EXECUTED audit row. Used by the orchestrator (immediate actions)
and by the scheduler (deferred retries).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_event
from app.core.logging import get_logger
from app.execution.base import ExecutionResult, Executor
from app.execution.executors import ALL_EXECUTORS
from app.models import enums
from app.models.entities import InterventionPlan, PaymentEvent, RiskEvent

log = get_logger(__name__)
ACTOR = "execution-layer@1.0.0"

# action_type → executor instance.
_REGISTRY: dict[enums.ActionType, Executor] = {
    at: ex for ex in ALL_EXECUTORS for at in ex.action_types
}


async def execute_plan(
    session: AsyncSession, plan_id: uuid.UUID, *, dry_run: bool = False
) -> ExecutionResult:
    """Execute one intervention plan and record the outcome."""
    plan = await session.get(InterventionPlan, plan_id)
    if plan is None:
        raise ValueError(f"plan {plan_id} not found")
    risk = await session.get(RiskEvent, plan.risk_event_id)
    pe = (
        await session.get(PaymentEvent, risk.payment_event_id)
        if risk and risk.payment_event_id
        else None
    )

    executor = _REGISTRY.get(plan.action_type)
    if executor is None:
        raise ValueError(f"no executor for action {plan.action_type}")

    if not await executor.max_frequency_check(session, plan, risk):
        plan.status = enums.PlanStatus.cancelled
        await write_audit_event(
            session, event_type="ACTION_SUPPRESSED", actor=ACTOR,
            merchant_id=risk.merchant_id, entity_type="InterventionPlan", entity_id=plan.plan_id,
            correlation_id=risk.risk_event_id,
            payload={"action_type": plan.action_type.value, "reason": "frequency_cap"},
        )
        await session.commit()
        return ExecutionResult(enums.PlanStatus.cancelled, "frequency cap hit", 0)

    result = await executor.execute(session, plan, risk, pe, dry_run=dry_run)

    if not dry_run:
        plan.status = result.status
        plan.executed_at = datetime.now(UTC)
        await write_audit_event(
            session, event_type="ACTION_EXECUTED", actor=ACTOR,
            merchant_id=risk.merchant_id, entity_type="InterventionPlan", entity_id=plan.plan_id,
            correlation_id=risk.risk_event_id,
            payload={
                "action_type": plan.action_type.value,
                "channel": plan.channel.value if plan.channel else None,
                "status": result.status.value,
                "detail": result.detail,
                "cost_paise": result.cost_paise,
                "is_reversible": executor.is_reversible,
                "outbox_id": str(result.outbox_id) if result.outbox_id else None,
            },
        )
        await session.commit()

    log.info(
        "execute_plan.done",
        plan_id=str(plan_id),
        action=plan.action_type.value,
        status=result.status.value,
    )
    return result
