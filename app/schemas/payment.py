"""Schemas for payment-event ingestion (the normalized shape both paths produce)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import enums


class PaymentEventIn(BaseModel):
    """Normalized payment event — the single shape fed to ``ingest_payment_event``.

    Produced from a Razorpay webhook (Path A) or the synthetic injector (Path B).
    """

    merchant_id: uuid.UUID | None = None  # resolved to the demo merchant if omitted
    gateway: enums.Gateway = enums.Gateway.synthetic
    gateway_event_id: str | None = None
    event_type: enums.EventType
    amount_paise: int = 0
    currency: str = "INR"
    customer_id: str | None = None
    customer_phone: str | None = None
    customer_email: str | None = None
    payment_method: dict = Field(default_factory=dict)
    error_code: str | None = None
    error_description: str | None = None
    raw_payload: dict = Field(default_factory=dict)


class PaymentEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: uuid.UUID
    merchant_id: uuid.UUID
    gateway: enums.Gateway
    event_type: enums.EventType
    amount_paise: int
    currency: str
    customer_id: str | None
    error_code: str | None
    error_description: str | None
    received_at: datetime
