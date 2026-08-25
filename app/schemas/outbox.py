"""Outbox (message dispatch) schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import enums


class OutboxOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    outbox_id: uuid.UUID
    plan_id: uuid.UUID | None
    channel: enums.Channel
    recipient: str | None
    subject: str | None
    body: str | None
    status: enums.OutboxStatus
    cost_paise: int
    created_at: datetime
