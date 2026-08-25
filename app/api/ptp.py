"""Promise-to-Pay API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_event
from app.core.bootstrap import resolve_merchant_id
from app.core.db import get_session
from app.models import enums
from app.models.entities import PromiseToPay
from app.schemas.ptp import PTPCreate, PTPOut

router = APIRouter(prefix="/v1/promises-to-pay", tags=["promises-to-pay"])


@router.post("", response_model=PTPOut, status_code=201)
async def create_ptp(body: PTPCreate, session: AsyncSession = Depends(get_session)) -> PromiseToPay:
    merchant_id = await resolve_merchant_id(session, body.merchant_id)
    ptp = PromiseToPay(
        merchant_id=merchant_id,
        customer_id=body.customer_id,
        invoice_id=body.invoice_id,
        promised_amount_paise=body.promised_amount_paise,
        promised_date=body.promised_date,
        logged_by=body.logged_by,
        status=enums.PTPStatus.active,
    )
    session.add(ptp)
    await session.flush()
    await write_audit_event(
        session, event_type="PROMISE_TO_PAY_LOGGED", actor=f"human:{body.logged_by}",
        merchant_id=merchant_id, entity_type="PromiseToPay", entity_id=ptp.ptp_id,
        payload={
            "customer_id": body.customer_id,
            "promised_amount_paise": body.promised_amount_paise,
            "promised_date": body.promised_date.isoformat(),
        },
    )
    await session.commit()
    await session.refresh(ptp)
    return ptp


@router.get("", response_model=list[PTPOut])
async def list_ptp(
    session: AsyncSession = Depends(get_session),
    status: enums.PTPStatus | None = None,
) -> list[PromiseToPay]:
    stmt = select(PromiseToPay).order_by(PromiseToPay.promised_date.asc())
    if status is not None:
        stmt = stmt.where(PromiseToPay.status == status)
    return list((await session.execute(stmt)).scalars().all())


@router.post("/{ptp_id}/kept", response_model=PTPOut)
async def mark_kept(
    ptp_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> PromiseToPay:
    ptp = await session.get(PromiseToPay, ptp_id)
    if ptp is None:
        raise HTTPException(status_code=404, detail="PTP not found")
    ptp.status = enums.PTPStatus.kept
    await write_audit_event(
        session, event_type="PROMISE_KEPT", actor="ops", merchant_id=ptp.merchant_id,
        entity_type="PromiseToPay", entity_id=ptp.ptp_id, payload={"customer_id": ptp.customer_id},
    )
    await session.commit()
    await session.refresh(ptp)
    return ptp
