"""ARIA ORM models (SQLAlchemy 2.0).

Mirrors the data model in the blueprint (§7). Enums are stored as VARCHAR
(``native_enum=False``) for painless migrations. Money is always integer paise.
PII columns use ``EncryptedString`` for at-rest encryption.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.crypto import EncryptedString
from app.core.db import Base
from app.models import enums


def _uuid_col() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


def _enum(py_enum: type, name: str) -> Enum:
    return Enum(py_enum, native_enum=False, length=40, name=name, validate_strings=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Merchant(Base, TimestampMixin):
    __tablename__ = "merchants"

    merchant_id: Mapped[uuid.UUID] = _uuid_col()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_hash: Mapped[str | None] = mapped_column(String(128))
    # thresholds, channels, stopping_rules, hinglish_mode, escalation_email, ...
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class PaymentEvent(Base):
    """Normalized payment event from any gateway or the synthetic injector."""

    __tablename__ = "payment_events"

    event_id: Mapped[uuid.UUID] = _uuid_col()
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merchants.merchant_id"), index=True, nullable=False
    )
    gateway: Mapped[enums.Gateway] = mapped_column(_enum(enums.Gateway, "gateway"))
    gateway_event_id: Mapped[str | None] = mapped_column(String(128), index=True)
    event_type: Mapped[enums.EventType] = mapped_column(_enum(enums.EventType, "event_type"))
    amount_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    customer_id: Mapped[str | None] = mapped_column(String(128), index=True)
    customer_phone: Mapped[str | None] = mapped_column(EncryptedString(512))
    customer_email: Mapped[str | None] = mapped_column(EncryptedString(512))
    payment_method: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(64), index=True)
    error_description: Mapped[str | None] = mapped_column(String(512))
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class RiskEvent(Base):
    __tablename__ = "risk_events"

    risk_event_id: Mapped[uuid.UUID] = _uuid_col()
    payment_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payment_events.event_id"), index=True
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merchants.merchant_id"), index=True, nullable=False
    )
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_signals: Mapped[list] = mapped_column(JSONB, default=list)
    workflow_type: Mapped[enums.WorkflowType] = mapped_column(
        _enum(enums.WorkflowType, "workflow_type"), index=True
    )
    status: Mapped[enums.RiskStatus] = mapped_column(
        _enum(enums.RiskStatus, "risk_status"), default=enums.RiskStatus.detected, index=True
    )
    amount_at_risk_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    diagnosis_id: Mapped[uuid.UUID] = _uuid_col()
    risk_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("risk_events.risk_event_id"), index=True, nullable=False
    )
    root_cause_category: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    reasoning_chain: Mapped[str | None] = mapped_column(Text)  # stored verbatim
    evidence_signals: Mapped[dict] = mapped_column(JSONB, default=dict)
    recommended_intervention_class: Mapped[str | None] = mapped_column(String(64))
    urgency_score: Mapped[float] = mapped_column(Float, default=0.0)
    diagnosed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    llm_model: Mapped[str | None] = mapped_column(String(128))
    llm_prompt_version: Mapped[str | None] = mapped_column(String(32))
    input_token_count: Mapped[int] = mapped_column(Integer, default=0)
    output_token_count: Mapped[int] = mapped_column(Integer, default=0)


class InterventionPlan(Base):
    __tablename__ = "intervention_plans"

    plan_id: Mapped[uuid.UUID] = _uuid_col()
    diagnosis_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("diagnoses.diagnosis_id"), index=True
    )
    risk_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("risk_events.risk_event_id"), index=True, nullable=False
    )
    action_type: Mapped[enums.ActionType] = mapped_column(_enum(enums.ActionType, "action_type"))
    channel: Mapped[enums.Channel | None] = mapped_column(_enum(enums.Channel, "channel"))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    message_content: Mapped[str | None] = mapped_column(EncryptedString(8192))
    attribution_window_hours: Mapped[int] = mapped_column(Integer, default=48)
    estimated_cost_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[enums.PlanStatus] = mapped_column(
        _enum(enums.PlanStatus, "plan_status"), default=enums.PlanStatus.planned
    )


class RecoveryRecord(Base):
    __tablename__ = "recovery_records"

    recovery_id: Mapped[uuid.UUID] = _uuid_col()
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("intervention_plans.plan_id"), index=True
    )
    risk_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("risk_events.risk_event_id"), index=True, nullable=False
    )
    outcome: Mapped[enums.RecoveryOutcome] = mapped_column(
        _enum(enums.RecoveryOutcome, "recovery_outcome")
    )
    recovered_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    payment_event_id_recovered: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payment_events.event_id")
    )
    attribution_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    recovery_cost_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    """Append-only ledger. App code never updates or deletes rows here."""

    __tablename__ = "audit_events"

    audit_id: Mapped[uuid.UUID] = _uuid_col()
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("merchants.merchant_id"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    actor: Mapped[str | None] = mapped_column(String(128))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    checksum: Mapped[str] = mapped_column(String(64))  # SHA-256 of payload
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class PromiseToPay(Base):
    __tablename__ = "promises_to_pay"

    ptp_id: Mapped[uuid.UUID] = _uuid_col()
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merchants.merchant_id"), index=True, nullable=False
    )
    customer_id: Mapped[str] = mapped_column(String(128), index=True)
    invoice_id: Mapped[str | None] = mapped_column(String(128))
    promised_amount_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    promised_date: Mapped[date] = mapped_column(Date)
    logged_by: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[enums.PTPStatus] = mapped_column(
        _enum(enums.PTPStatus, "ptp_status"), default=enums.PTPStatus.active
    )
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DNCEntry(Base):
    __tablename__ = "dnc_entries"

    dnc_id: Mapped[uuid.UUID] = _uuid_col()
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merchants.merchant_id"), index=True, nullable=False
    )
    customer_identifier: Mapped[str] = mapped_column(String(128), index=True)  # hashed phone/email
    reason: Mapped[str | None] = mapped_column(String(255))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    added_by: Mapped[str | None] = mapped_column(String(128))


class Outbox(Base):
    """Stubbed message dispatch — rendered content shown in the dashboard, never sent."""

    __tablename__ = "outbox"

    outbox_id: Mapped[uuid.UUID] = _uuid_col()
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merchants.merchant_id"), index=True, nullable=False
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("intervention_plans.plan_id"), index=True
    )
    channel: Mapped[enums.Channel] = mapped_column(_enum(enums.Channel, "outbox_channel"))
    recipient: Mapped[str | None] = mapped_column(EncryptedString(512))
    subject: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(EncryptedString(8192))
    status: Mapped[enums.OutboxStatus] = mapped_column(
        _enum(enums.OutboxStatus, "outbox_status"), default=enums.OutboxStatus.queued
    )
    cost_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
