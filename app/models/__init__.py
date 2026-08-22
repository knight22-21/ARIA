"""ORM models. Importing this package registers every table on ``Base.metadata``."""

from app.core.db import Base
from app.models.entities import (
    AuditEvent,
    Diagnosis,
    DNCEntry,
    InterventionPlan,
    Merchant,
    Outbox,
    PaymentEvent,
    PromiseToPay,
    RecoveryRecord,
    RiskEvent,
)

__all__ = [
    "Base",
    "AuditEvent",
    "Diagnosis",
    "DNCEntry",
    "InterventionPlan",
    "Merchant",
    "Outbox",
    "PaymentEvent",
    "PromiseToPay",
    "RecoveryRecord",
    "RiskEvent",
]
