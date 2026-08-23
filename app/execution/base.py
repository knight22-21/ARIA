"""Execution layer — base types for the bounded action space.

Every action ARIA can take has a typed executor with a uniform contract:
  - is_reversible      — reversibility class (audit / safety)
  - estimate_cost      — paise cost for the Recovery P&L
  - max_frequency_check — may this action run again for this case?
  - execute            — perform it (honouring dry_run)
"""

from __future__ import annotations

import abc
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import enums
from app.models.entities import InterventionPlan, PaymentEvent, RiskEvent


@dataclass
class ExecutionResult:
    status: enums.PlanStatus
    detail: str
    cost_paise: int = 0
    outbox_id: uuid.UUID | None = None


class Executor(abc.ABC):
    """Base class for a single bounded action."""

    action_types: set[enums.ActionType] = set()
    is_reversible: bool = True

    def estimate_cost(self, plan: InterventionPlan) -> int:
        return plan.estimated_cost_paise or 0

    async def max_frequency_check(
        self, session: AsyncSession, plan: InterventionPlan, risk: RiskEvent
    ) -> bool:
        """Return True if the action is allowed to run (frequency cap not hit)."""
        return True

    @abc.abstractmethod
    async def execute(
        self,
        session: AsyncSession,
        plan: InterventionPlan,
        risk: RiskEvent,
        payment_event: PaymentEvent | None,
        *,
        dry_run: bool = False,
    ) -> ExecutionResult: ...
