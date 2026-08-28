"""Append-only audit ledger writer.

Every significant decision/action calls ``write_audit_event``. Each row carries a
SHA-256 checksum of its payload for tamper detection (a nightly job re-verifies).
App code only ever INSERTs here — never UPDATE/DELETE.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.entities import AuditEvent

log = get_logger(__name__)

# Redis pub/sub channel the SSE stream listens on. Each audit write announces here
# the instant it happens, so the dashboard sees pipeline steps live, one by one.
EVENT_CHANNEL = "aria:events"


def compute_checksum(payload: dict[str, Any]) -> str:
    """Deterministic SHA-256 over the payload (sorted keys, compact separators)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


async def _publish_event(
    event_type: str,
    actor: str,
    entity_id: uuid.UUID | None,
    merchant_id: uuid.UUID | None,
    correlation_id: uuid.UUID | None,
) -> None:
    """Fire-and-forget announce to the live event stream (never fatal).

    ``correlation_id`` (the risk-event id) ties every step of one run together so the
    dashboard can scope the feed to a single triggered run.
    """
    try:
        from app.core.redis import get_redis

        corr = correlation_id or entity_id
        msg = json.dumps(
            {
                "event_type": event_type,
                "actor": actor,
                "entity_id": str(entity_id) if entity_id else None,
                "correlation_id": str(corr) if corr else None,
                "merchant_id": str(merchant_id) if merchant_id else None,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        await get_redis().publish(EVENT_CHANNEL, msg)
    except Exception as exc:  # noqa: BLE001 — streaming is best-effort
        log.debug("audit.publish_failed", error=str(exc))


async def write_audit_event(
    session: AsyncSession,
    *,
    event_type: str,
    actor: str,
    merchant_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    correlation_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    flush: bool = True,
) -> AuditEvent:
    """Insert one audit row. Does not commit — caller owns the transaction.

    ``correlation_id`` groups a run's events for the live feed; when omitted it
    defaults to ``entity_id`` (correct for events whose entity is the RiskEvent).
    """
    payload = payload or {}
    event = AuditEvent(
        merchant_id=merchant_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        payload=payload,
        checksum=compute_checksum(payload),
    )
    session.add(event)
    if flush:
        await session.flush()
    await _publish_event(event_type, actor, entity_id, merchant_id, correlation_id)
    return event
