"""Structured contracts for agent inputs/outputs.

These Pydantic models are what the LLM agents must emit (validated at the
tool-call/parse layer) and what the orchestrator passes between nodes.
"""

from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models import enums

# ---- Diagnostic agent ------------------------------------------------


class DiagnosisResult(BaseModel):
    """Structured verdict from the Diagnostic agent."""

    reasoning: str = Field(description="Chain-of-thought: technical, behavioral, risk analysis.")
    root_cause_category: str = Field(description="e.g. SOFT_DECLINE_BANK_SIDE, MANDATE_EXPIRED")
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    recommended_intervention_class: str = Field(description="e.g. TIMED_RETRY, ALT_PAYMENT_LINK")
    urgency_score: float = Field(ge=0.0, le=1.0, default=0.5)


# ---- Intervention selector ------------------------------------------


class InterventionResult(BaseModel):
    """Chosen action from the bounded action space + generated content."""

    reasoning: str
    action_type: enums.ActionType
    channel: enums.Channel | None = None
    message_content: str | None = None
    scheduled_offset_hours: float = Field(
        default=0.0, description="Hours from now to execute; 0 = immediately."
    )
    attribution_window_hours: int = 48
    fallback_action: enums.ActionType | None = None


# ---- Escalation agent -----------------------------------------------


class VoiceScriptResult(BaseModel):
    """Hinglish voice call script + SSML preview (no call placed)."""

    script: str
    ssml: str
    tone_notes: str = ""


class UrgencyLevel(StrEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class EscalationPackage(BaseModel):
    """Human-review package prepared by the Escalation agent."""

    summary: str
    urgency: UrgencyLevel
    recommended_action: str
    reason_escalated: str
    what_was_tried: list[str] = Field(default_factory=list)


# ---- Orchestrator state ---------------------------------------------


class PolicyDecision(BaseModel):
    """Outcome of the deterministic stopping-rules / policy check."""

    allowed: bool
    action: str  # "proceed" | "suppress" | "escalate"
    fired_rules: list[str] = Field(default_factory=list)
    reason: str = ""


class OrchestratorState(BaseModel):
    """Typed state threaded through every LangGraph node."""

    risk_event_id: uuid.UUID
    merchant_id: uuid.UUID
    workflow_type: enums.WorkflowType
    amount_at_risk_paise: int = 0

    policy: PolicyDecision | None = None
    diagnosis: DiagnosisResult | None = None
    intervention: InterventionResult | None = None
    escalation: EscalationPackage | None = None

    # Terminal outcome for observability: proceeded | escalated | suppressed
    outcome: str | None = None
    diagnosis_id: uuid.UUID | None = None
    plan_id: uuid.UUID | None = None
