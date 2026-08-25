"""B2B invoice CSV import.

Accepts a CSV with strict columns:
    invoice_id, customer_name, customer_email, customer_phone, amount, due_date, currency
Amounts are rupees (float/int); stored as integer paise. due_date is ISO (YYYY-MM-DD).
Idempotent per (merchant, invoice_id): re-importing updates the existing row.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.entities import Invoice

log = get_logger(__name__)

REQUIRED_COLUMNS = {
    "invoice_id",
    "customer_name",
    "customer_email",
    "customer_phone",
    "amount",
    "due_date",
}
MAX_ROWS = 10_000


class CSVValidationError(ValueError):
    """Raised on malformed invoice CSV."""


def _to_paise(raw: str) -> int:
    return int(round(float(str(raw).replace(",", "").strip()) * 100))


async def import_invoices_csv(
    session: AsyncSession, csv_text: str, merchant_id: uuid.UUID
) -> dict:
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        raise CSVValidationError("empty CSV")
    headers = {h.strip() for h in reader.fieldnames}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        raise CSVValidationError(f"missing required columns: {sorted(missing)}")

    imported, updated, errors = 0, 0, []
    for i, row in enumerate(reader, start=2):  # header is line 1
        if i - 1 > MAX_ROWS:
            raise CSVValidationError(f"too many rows (>{MAX_ROWS})")
        try:
            ref = (row.get("invoice_id") or "").strip()
            if not ref:
                raise CSVValidationError("blank invoice_id")
            amount_paise = _to_paise(row["amount"])
            due = date.fromisoformat(row["due_date"].strip())
            currency = (row.get("currency") or "INR").strip() or "INR"

            existing = await session.scalar(
                select(Invoice).where(
                    Invoice.merchant_id == merchant_id, Invoice.invoice_ref == ref
                )
            )
            if existing:
                existing.amount_paise = amount_paise
                existing.due_date = due
                existing.currency = currency
                updated += 1
            else:
                session.add(
                    Invoice(
                        merchant_id=merchant_id,
                        invoice_ref=ref,
                        customer_id=(row.get("customer_email") or ref).strip(),
                        customer_name=(row.get("customer_name") or "").strip() or None,
                        customer_email=(row.get("customer_email") or "").strip() or None,
                        customer_phone=(row.get("customer_phone") or "").strip() or None,
                        amount_paise=amount_paise,
                        currency=currency,
                        due_date=due,
                    )
                )
                imported += 1
        except (ValueError, KeyError) as exc:
            errors.append({"line": i, "error": str(exc)})

    await session.commit()
    log.info("invoices.imported", imported=imported, updated=updated, errors=len(errors))
    return {"imported": imported, "updated": updated, "errors": errors}
