"""Domain enumerations shared by ORM models and Pydantic schemas."""

from enum import StrEnum


class Gateway(StrEnum):
    razorpay = "razorpay"
    stripe = "stripe"
    cashfree = "cashfree"
    synthetic = "synthetic"  # injector-sourced events


class EventType(StrEnum):
    payment_failed = "payment_failed"
    payment_captured = "payment_captured"
    checkout_created = "checkout_created"
    checkout_abandoned = "checkout_abandoned"
    subscription_charged = "subscription_charged"
    subscription_halted = "subscription_halted"
    mandate_confirmed = "mandate_confirmed"
    mandate_rejected = "mandate_rejected"
    mandate_debited = "mandate_debited"
    invoice_overdue = "invoice_overdue"


class WorkflowType(StrEnum):
    payment_degradation = "payment_degradation"
    checkout_abandonment = "checkout_abandonment"
    subscription_failure = "subscription_failure"
    b2b_receivable = "b2b_receivable"
    mandate_retry = "mandate_retry"


class RiskStatus(StrEnum):
    detected = "detected"
    in_progress = "in_progress"
    recovered = "recovered"
    unrecovered = "unrecovered"
    escalated = "escalated"
    suppressed = "suppressed"


class ActionType(StrEnum):
    retry_payment = "retry_payment"
    send_payment_link = "send_payment_link"
    send_card_update = "send_card_update"
    offer_emi = "offer_emi"
    send_mandate_relink = "send_mandate_relink"
    send_invoice_reminder = "send_invoice_reminder"
    send_payment_plan = "send_payment_plan"
    waive_late_fee = "waive_late_fee"
    schedule_retry = "schedule_retry"
    generate_voice_script = "generate_voice_script"
    trigger_ivr_call = "trigger_ivr_call"
    escalate_human = "escalate_human"
    flag_write_off = "flag_write_off"
    suppress = "suppress"


class Channel(StrEnum):
    whatsapp = "whatsapp"
    sms = "sms"
    email = "email"
    ivr = "ivr"
    internal_retry = "internal_retry"


class PlanStatus(StrEnum):
    planned = "planned"
    executing = "executing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class RecoveryOutcome(StrEnum):
    recovered = "recovered"
    unrecovered = "unrecovered"
    partial = "partial"
    bounced = "bounced"
    dnc_hit = "dnc_hit"
    stopped = "stopped"


class PTPStatus(StrEnum):
    active = "active"
    kept = "kept"
    broken = "broken"
    partial = "partial"


class OutboxStatus(StrEnum):
    queued = "queued"
    sent = "sent"
    delivered = "delivered"
    failed = "failed"
    bounced = "bounced"
    read = "read"
