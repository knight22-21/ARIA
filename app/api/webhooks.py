"""Inbound webhook endpoints (Path A). Fast-ack; heavy work is enqueued."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.logging import get_logger
from app.ingestion.normalize import normalize_razorpay
from app.ingestion.service import ingest_payment_event
from app.integrations.razorpay import verify_webhook_signature

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
log = get_logger(__name__)


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    raw = await request.body()

    if not verify_webhook_signature(raw, x_razorpay_signature or ""):
        log.warning("webhook.razorpay.bad_signature")
        raise HTTPException(status_code=403, detail="invalid signature")

    body = await request.json()
    payload = normalize_razorpay(body)
    # Enqueue detection (inline=False) so we ack the webhook in <200ms.
    await ingest_payment_event(session, payload, inline=False)
    return {"status": "accepted"}
