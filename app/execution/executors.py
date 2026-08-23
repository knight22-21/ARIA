"""Concrete executors for the bounded action space.

Messaging is *stubbed*: rendered content is written to the Outbox (and shown in the
dashboard) — nothing is actually sent. Retries use Razorpay test mode when wired,
otherwise they are simulated. Every executor is idempotent-friendly and cheap.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.execution.base import ExecutionResult, Executor
from app.models import enums
from app.models.entities import InterventionPlan, Outbox, PaymentEvent, RiskEvent

log = get_logger(__name__)

# Channel → default recipient field.
_MSG_COST_PAISE = 150
_IVR_COST_PAISE = 500
GLOBAL_MAX_RETRIES = 5


class MessageExecutor(Executor):
    """Stubbed dispatcher for all message-based actions → writes to Outbox."""

    action_types = {
        enums.ActionType.send_payment_link,
        enums.ActionType.send_card_update,
        enums.ActionType.offer_emi,
        enums.ActionType.send_mandate_relink,
        enums.ActionType.send_invoice_reminder,
        enums.ActionType.send_payment_plan,
    }
    is_reversible = True

    def estimate_cost(self, plan: InterventionPlan) -> int:
        return _MSG_COST_PAISE

    async def max_frequency_check(
        self, session: AsyncSession, plan: InterventionPlan, risk: RiskEvent
    ) -> bool:
        # Don't send two messages for the same plan.
        already = await session.scalar(
            select(func.count()).select_from(Outbox).where(Outbox.plan_id == plan.plan_id)
        )
        return not already

    async def execute(
        self,
        session: AsyncSession,
        plan: InterventionPlan,
        risk: RiskEvent,
        payment_event: PaymentEvent | None,
        *,
        dry_run: bool = False,
    ) -> ExecutionResult:
        channel = plan.channel or enums.Channel.whatsapp
        recipient = None
        if payment_event is not None:
            recipient = (
                payment_event.customer_email
                if channel == enums.Channel.email
                else payment_event.customer_phone
            )
        if dry_run:
            return ExecutionResult(enums.PlanStatus.planned, "dry-run", self.estimate_cost(plan))

        outbox = Outbox(
            merchant_id=risk.merchant_id,
            plan_id=plan.plan_id,
            channel=channel,
            recipient=recipient,
            subject=None,
            body=plan.message_content,
            status=enums.OutboxStatus.sent,
            cost_paise=_MSG_COST_PAISE,
        )
        session.add(outbox)
        await session.flush()
        return ExecutionResult(
            enums.PlanStatus.completed, f"message queued to outbox via {channel.value}",
            _MSG_COST_PAISE, outbox.outbox_id,
        )


class RetryPaymentExecutor(Executor):
    """Retry a payment. Check-before-act; Razorpay test mode when wired, else simulated."""

    action_types = {enums.ActionType.retry_payment}
    is_reversible = True

    def estimate_cost(self, plan: InterventionPlan) -> int:
        return 0  # gateway fee only

    async def max_frequency_check(
        self, session: AsyncSession, plan: InterventionPlan, risk: RiskEvent
    ) -> bool:
        count = await session.scalar(
            select(func.count())
            .select_from(InterventionPlan)
            .where(
                InterventionPlan.risk_event_id == risk.risk_event_id,
                InterventionPlan.action_type == enums.ActionType.retry_payment,
                InterventionPlan.status == enums.PlanStatus.completed,
            )
        )
        return (count or 0) < GLOBAL_MAX_RETRIES

    async def execute(
        self,
        session: AsyncSession,
        plan: InterventionPlan,
        risk: RiskEvent,
        payment_event: PaymentEvent | None,
        *,
        dry_run: bool = False,
    ) -> ExecutionResult:
        # Check-before-act: never retry a cancelled/already-successful case.
        if risk.status in {enums.RiskStatus.recovered, enums.RiskStatus.suppressed}:
            return ExecutionResult(enums.PlanStatus.cancelled, "aborted: case already resolved", 0)
        if dry_run:
            return ExecutionResult(enums.PlanStatus.planned, "dry-run", 0)
        # Razorpay test-mode retry would go here; in this build we log the attempt and
        # let a subsequent payment.captured event drive attribution.
        log.info("retry.attempted", risk_event_id=str(risk.risk_event_id))
        return ExecutionResult(enums.PlanStatus.completed, "retry attempted via gateway (test)", 0)


class ScheduleRetryExecutor(Executor):
    """Register a future retry. The Scheduler/Beat picks it up at scheduled_at."""

    action_types = {enums.ActionType.schedule_retry}
    is_reversible = True

    async def execute(
        self,
        session: AsyncSession,
        plan: InterventionPlan,
        risk: RiskEvent,
        payment_event: PaymentEvent | None,
        *,
        dry_run: bool = False,
    ) -> ExecutionResult:
        when = plan.scheduled_at.isoformat() if plan.scheduled_at else "unset"
        return ExecutionResult(enums.PlanStatus.planned, f"retry scheduled for {when}", 0)


class VoiceScriptExecutor(Executor):
    """Generate a Hinglish call script → stored as an Outbox 'ivr' preview (no call placed)."""

    action_types = {enums.ActionType.generate_voice_script, enums.ActionType.trigger_ivr_call}
    is_reversible = True

    def estimate_cost(self, plan: InterventionPlan) -> int:
        return _IVR_COST_PAISE if plan.action_type == enums.ActionType.trigger_ivr_call else 0

    async def execute(
        self,
        session: AsyncSession,
        plan: InterventionPlan,
        risk: RiskEvent,
        payment_event: PaymentEvent | None,
        *,
        dry_run: bool = False,
    ) -> ExecutionResult:
        if dry_run:
            return ExecutionResult(enums.PlanStatus.planned, "dry-run", self.estimate_cost(plan))
        outbox = Outbox(
            merchant_id=risk.merchant_id,
            plan_id=plan.plan_id,
            channel=enums.Channel.ivr,
            recipient=payment_event.customer_phone if payment_event else None,
            subject="voice script",
            body=plan.message_content,
            status=enums.OutboxStatus.queued,
            cost_paise=self.estimate_cost(plan),
        )
        session.add(outbox)
        await session.flush()
        return ExecutionResult(
            enums.PlanStatus.completed, "voice script prepared", self.estimate_cost(plan),
            outbox.outbox_id,
        )


class NoOpExecutor(Executor):
    """Terminal / account-side actions with no message dispatch in this build."""

    action_types = {
        enums.ActionType.suppress,
        enums.ActionType.flag_write_off,
        enums.ActionType.escalate_human,
        enums.ActionType.waive_late_fee,  # would post a credit in a real billing system
    }
    is_reversible = False

    async def execute(
        self,
        session: AsyncSession,
        plan: InterventionPlan,
        risk: RiskEvent,
        payment_event: PaymentEvent | None,
        *,
        dry_run: bool = False,
    ) -> ExecutionResult:
        return ExecutionResult(
            enums.PlanStatus.completed, f"{plan.action_type.value} (no dispatch)", 0
        )


ALL_EXECUTORS: list[Executor] = [
    MessageExecutor(),
    RetryPaymentExecutor(),
    ScheduleRetryExecutor(),
    VoiceScriptExecutor(),
    NoOpExecutor(),
]
