"""Workflow classifier — maps a payment event to the recovery workflow it belongs to."""

from __future__ import annotations

from app.models import enums

_EVENT_TO_WORKFLOW: dict[enums.EventType, enums.WorkflowType] = {
    enums.EventType.payment_failed: enums.WorkflowType.payment_degradation,
    enums.EventType.checkout_created: enums.WorkflowType.checkout_abandonment,
    enums.EventType.checkout_abandoned: enums.WorkflowType.checkout_abandonment,
    enums.EventType.subscription_charged: enums.WorkflowType.subscription_failure,
    enums.EventType.subscription_halted: enums.WorkflowType.subscription_failure,
    enums.EventType.mandate_debited: enums.WorkflowType.mandate_retry,
    enums.EventType.mandate_rejected: enums.WorkflowType.mandate_retry,
    enums.EventType.invoice_overdue: enums.WorkflowType.b2b_receivable,
}


def classify_workflow(event_type: enums.EventType) -> enums.WorkflowType:
    return _EVENT_TO_WORKFLOW.get(event_type, enums.WorkflowType.payment_degradation)
