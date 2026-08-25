"""B2B invoice API — CSV import and aging scan."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bootstrap import resolve_merchant_id
from app.core.db import get_session
from app.detection.aging import scan_invoices
from app.ingestion.invoices import CSVValidationError, import_invoices_csv

router = APIRouter(prefix="/v1/invoices", tags=["invoices"])


@router.post("/import")
async def import_invoices(
    file: UploadFile = File(...),
    merchant_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    raw = (await file.read()).decode("utf-8", errors="replace")
    mid = await resolve_merchant_id(session, merchant_id)
    try:
        return await import_invoices_csv(session, raw, mid)
    except CSVValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/scan")
async def scan(session: AsyncSession = Depends(get_session)) -> dict:
    """Run the invoice aging scanner now (Celery Beat runs it nightly in prod)."""
    return await scan_invoices(session)
