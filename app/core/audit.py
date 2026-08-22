"""Append-only audit ledger writer.

Every significant decision/action calls ``write_audit_event``. Each row carries a
SHA-256 checksum of its payload for tamper detection (a nightly job re-verifies).
App code only ever INSERTs here — never UPDATE/DELETE.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AuditEvent


def compute_checksum(payload: dict[str, Any]) -> str:
    """Deterministic SHA-256 over the payload (sorted keys, compact separators)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


async def write_audit_event(
    session: AsyncSession,
    *,
    event_type: str,
    actor: str,
    merchant_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    flush: bool = True,
) -> AuditEvent:
    """Insert one audit row. Does not commit — caller owns the transaction."""
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
    return event
