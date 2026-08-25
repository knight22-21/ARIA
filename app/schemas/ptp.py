"""Promise-to-Pay schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models import enums


class PTPCreate(BaseModel):
    customer_id: str
    invoice_id: str | None = None
    promised_amount_paise: int
    promised_date: date
    logged_by: str
    merchant_id: uuid.UUID | None = None


class PTPOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ptp_id: uuid.UUID
    customer_id: str
    invoice_id: str | None
    promised_amount_paise: int
    promised_date: date
    logged_by: str | None
    status: enums.PTPStatus
    reminder_sent_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
