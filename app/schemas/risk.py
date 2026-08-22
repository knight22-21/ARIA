"""Schemas for risk events (detection output + API responses)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import enums


class RiskSignal(BaseModel):
    signal_type: str
    value: float
    weight: float
    detail: str | None = None


class RiskEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    risk_event_id: uuid.UUID
    payment_event_id: uuid.UUID | None
    merchant_id: uuid.UUID
    risk_score: float
    risk_signals: list[dict]
    workflow_type: enums.WorkflowType
    status: enums.RiskStatus
    amount_at_risk_paise: int
    detected_at: datetime
    resolved_at: datetime | None
