"""Demo/default merchant bootstrap.

For this single-tenant build we operate one seeded merchant. Ingestion resolves
to it when a payload omits ``merchant_id``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Merchant

# Stable UUID so the demo merchant is deterministic across restarts/seeds.
DEMO_MERCHANT_ID = uuid.UUID("00000000-0000-0000-0000-0000000a71a0")

DEFAULT_CONFIG: dict = {
    "thresholds": {
        "min_cart_value_paise": 50_000,
        "auto_action_amount_ceiling_paise": 5_000_000,  # ₹50k
    },
    "channels": {
        "whatsapp_enabled": True,
        "sms_enabled": True,
        "email_enabled": True,
        "voice_enabled": True,
    },
    "stopping_rules": {
        "max_contacts_per_customer_7d": 6,
        "max_retries_per_payment": 3,
    },
    "hinglish_mode": True,
    "escalation_email": "ops@demo-merchant.example.com",
    "comms_window": {"start_hour": 8, "end_hour": 21},  # local time
}


async def get_or_create_demo_merchant(session: AsyncSession) -> Merchant:
    merchant = await session.get(Merchant, DEMO_MERCHANT_ID)
    if merchant is None:
        merchant = Merchant(
            merchant_id=DEMO_MERCHANT_ID,
            name="Demo Merchant (ARIA)",
            config=DEFAULT_CONFIG,
        )
        session.add(merchant)
        await session.flush()
    return merchant


async def resolve_merchant_id(session: AsyncSession, merchant_id: uuid.UUID | None) -> uuid.UUID:
    if merchant_id is not None:
        existing = await session.scalar(
            select(Merchant.merchant_id).where(Merchant.merchant_id == merchant_id)
        )
        if existing is not None:
            return existing
    merchant = await get_or_create_demo_merchant(session)
    return merchant.merchant_id
