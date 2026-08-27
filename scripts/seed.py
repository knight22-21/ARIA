"""Deterministic demo seed generator.

Populates a realistic 30-day backdrop so the dashboard looks alive on a cold start:
~500 customers, ~2000 payment events, risk events across every workflow and status,
diagnoses (with reasoning), interventions, outbox messages, recovery records (→ a real
P&L), a scripted HDFC bank-outage window, B2B invoices with an aging spread, PTPs and
DNC entries — all written directly (no LLM calls, so it's fast and repeatable).

The live injector (Command Center → Fire event) provides the real-time LLM reasoning
moment during the demo; this seed is the historical backdrop.

Usage:
    python scripts/seed.py            # wipe + seed
    python scripts/seed.py --keep     # seed without wiping
"""
# ruff: noqa: E501  (data-generation script — long template/constructor lines are fine)

from __future__ import annotations

import asyncio
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from faker import Faker  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from app.core.audit import write_audit_event  # noqa: E402
from app.core.bootstrap import get_or_create_demo_merchant  # noqa: E402
from app.core.crypto import hash_identifier  # noqa: E402
from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.detection.scorer import compute_score  # noqa: E402
from app.models import enums  # noqa: E402
from app.models.entities import (  # noqa: E402
    Diagnosis,
    DNCEntry,
    InterventionPlan,
    Invoice,
    Outbox,
    PaymentEvent,
    PromiseToPay,
    RecoveryRecord,
    RiskEvent,
)

SEED = 42
fake = Faker("en_IN")
Faker.seed(SEED)
random.seed(SEED)

BANKS = ["HDFC", "ICICI", "SBI", "AXIS", "KOTAK"]
NOW = datetime.now(UTC)
START = NOW - timedelta(days=30)

# root_cause → (workflow, action, channel, reasoning template, message template)
CATALOG = {
    "SOFT_DECLINE_BANK_SIDE": (
        enums.WorkflowType.payment_degradation, enums.ActionType.schedule_retry,
        enums.Channel.internal_retry,
        "Error code is an issuing-bank soft decline on {bank}. Customer paid successfully before; "
        "no card/behavioral red flags. Likely a transient bank-side block that clears on retry.",
        None,
    ),
    "INSUFFICIENT_FUNDS_BEHAVIORAL": (
        enums.WorkflowType.payment_degradation, enums.ActionType.send_payment_link,
        enums.Channel.whatsapp,
        "Repeated insufficient-funds failures on {bank} suggest an affordability pattern rather "
        "than a technical fault. A friendly payment link with flexibility is the best next step.",
        "Hi! Aapka payment ₹{amt} abhi complete nahi hua — balance ka issue lagta hai. Yahan tap "
        "karke aaram se pay kar dijiye: {{link}}",
    ),
    "TECHNICAL_GATEWAY": (
        enums.WorkflowType.payment_degradation, enums.ActionType.retry_payment,
        enums.Channel.internal_retry,
        "Gateway timeout during authorization on {bank}; not a decline. An immediate retry on the "
        "same rail is highly likely to succeed.",
        None,
    ),
    "BANK_OUTAGE": (
        enums.WorkflowType.payment_degradation, enums.ActionType.schedule_retry,
        enums.Channel.internal_retry,
        "Elevated failure rate across many {bank} cards in a short window indicates a bank-side "
        "outage. Suppress immediate retries and reschedule after the window.",
        None,
    ),
    "INSUFFICIENT_FUNDS_PREDICTABLE": (
        enums.WorkflowType.subscription_failure, enums.ActionType.send_payment_link,
        enums.Channel.whatsapp,
        "Autopay debit on {bank} failed for insufficient funds. Customer history shows funds usually "
        "arrive post-salary; a gentle link keeps the subscription active.",
        "Hi! Aapka subscription ka payment ₹{amt} process nahi ho paaya. Link se abhi complete kar "
        "dijiye, subscription chalu rahega: {{link}}",
    ),
    "MANDATE_EXPIRED": (
        enums.WorkflowType.subscription_failure, enums.ActionType.send_mandate_relink,
        enums.Channel.whatsapp,
        "The NACH/UPI Autopay mandate on {bank} has lapsed, so no debit was possible. Customer must "
        "re-register the mandate via a deep link.",
        "Aapka mandate expire ho gaya hai, isliye auto-payment nahi hua. 2 minute mein dobara set "
        "kijiye: {{link}}",
    ),
    "GOOD_PAYER_ADMINISTRATIVE_DELAY": (
        enums.WorkflowType.b2b_receivable, enums.ActionType.send_invoice_reminder,
        enums.Channel.email,
        "Enterprise customer with a clean history; invoice overdue likely due to an internal approval "
        "cycle. A soft, no-pressure reminder is appropriate.",
        "Namaste! Chhoti si reminder — invoice ₹{amt} ka payment pending hai. Aaram se process kar "
        "dijiyega. Dhanyavaad.",
    ),
    "CHRONIC_LATE_PAYER": (
        enums.WorkflowType.b2b_receivable, enums.ActionType.send_payment_plan,
        enums.Channel.whatsapp,
        "Customer is consistently 30–60 days late. A firmer reminder with a statement of account and "
        "a structured payment-plan offer is warranted.",
        "Namaste! Aapka invoice ₹{amt} kaafi din se pending hai. Aapke liye payment plan ka option "
        "hai — is link par set kar sakte hain: {{link}}",
    ),
}
ROOT_CAUSES = list(CATALOG)

# Outcome distribution for processed risk events.
OUTCOMES = (
    ["recovered"] * 60 + ["unrecovered"] * 12 + ["escalated"] * 14 + ["suppressed"] * 8 + ["in_progress"] * 6
)


async def _wipe(session) -> None:
    for model in (
        RecoveryRecord, Outbox, InterventionPlan, Diagnosis, PromiseToPay,
        DNCEntry, Invoice, RiskEvent, PaymentEvent,
    ):
        await session.execute(delete(model))
    # Audit is append-only in prod; for a clean demo seed we reset it too.
    from app.models.entities import AuditEvent

    await session.execute(delete(AuditEvent))
    await session.commit()


def _customers(n: int) -> list[dict]:
    out = []
    for _ in range(n):
        name = fake.name()
        out.append(
            {
                "id": fake.uuid4(),
                "name": name,
                "email": fake.company_email(),
                "phone": f"+9198{random.randint(10000000, 99999999)}",
            }
        )
    return out


async def _make_risk_chain(
    session, merchant_id, cust, amount_paise, root_cause, when, bank, outcome
) -> None:
    """Create a full risk→diagnosis→intervention→outcome record set for one case."""
    workflow, action, channel, reason_tpl, msg_tpl = CATALOG[root_cause]

    signal_values = {
        "error_code_severity": random.uniform(0.4, 0.7),
        "customer_failure_rate_7d": random.uniform(0.1, 0.9),
        "bank_failure_rate_1h": 0.8 if root_cause == "BANK_OUTAGE" else random.uniform(0, 0.2),
        "amount_percentile": min(1.0, amount_paise / 5_000_000),
        "subscription_health_score": random.uniform(0, 0.5),
        "fraud_proxy_score": 0.0,
    }
    score, signals = compute_score(signal_values)

    pe = PaymentEvent(
        merchant_id=merchant_id, gateway=enums.Gateway.razorpay,
        event_type=(
            enums.EventType.invoice_overdue if workflow == enums.WorkflowType.b2b_receivable
            else enums.EventType.subscription_halted if workflow == enums.WorkflowType.subscription_failure
            else enums.EventType.payment_failed
        ),
        amount_paise=amount_paise, currency="INR", customer_id=cust["id"],
        customer_phone=cust["phone"], customer_email=cust["email"],
        payment_method={"type": "card", "bank": bank}, error_code="do_not_honour",
        received_at=when,
    )
    session.add(pe)
    await session.flush()

    status_map = {
        "recovered": enums.RiskStatus.recovered, "unrecovered": enums.RiskStatus.unrecovered,
        "escalated": enums.RiskStatus.escalated, "suppressed": enums.RiskStatus.suppressed,
        "in_progress": enums.RiskStatus.in_progress,
    }
    risk = RiskEvent(
        payment_event_id=pe.event_id, merchant_id=merchant_id, risk_score=score,
        risk_signals=signals, workflow_type=workflow, status=status_map[outcome],
        amount_at_risk_paise=amount_paise, detected_at=when,
        resolved_at=(when + timedelta(hours=random.randint(2, 60)))
        if outcome in ("recovered", "unrecovered") else None,
    )
    session.add(risk)
    await session.flush()
    await write_audit_event(
        session, event_type="RISK_DETECTED", actor="detection-engine@0.1.0",
        merchant_id=merchant_id, entity_type="RiskEvent", entity_id=risk.risk_event_id,
        payload={"risk_score": score, "workflow_type": workflow.value},
    )

    if outcome == "suppressed":
        await write_audit_event(
            session, event_type="STOPPING_RULE_FIRED", actor="orchestrator@1.0.0",
            merchant_id=merchant_id, entity_type="RiskEvent", entity_id=risk.risk_event_id,
            payload={"fired_rules": ["DNC_CHECK"]},
        )
        return

    diag = Diagnosis(
        risk_event_id=risk.risk_event_id, root_cause_category=root_cause,
        confidence=round(random.uniform(0.68, 0.92), 2),
        reasoning_chain=reason_tpl.format(bank=bank, amt=amount_paise // 100),
        evidence_signals={"detector_signals": signals}, recommended_intervention_class="AUTO",
        urgency_score=round(random.uniform(0.3, 0.8), 2), llm_model="groq:openai/gpt-oss-120b",
        llm_prompt_version="1.0.0", input_token_count=720, output_token_count=540,
    )
    session.add(diag)
    await session.flush()
    await write_audit_event(
        session, event_type="DIAGNOSIS_PRODUCED", actor="diagnostic-agent@1.0.0",
        merchant_id=merchant_id, entity_type="Diagnosis", entity_id=diag.diagnosis_id,
        payload={"root_cause_category": root_cause, "confidence": diag.confidence},
    )

    if outcome == "escalated":
        await write_audit_event(
            session, event_type="ESCALATION_RAISED", actor="escalation-agent@1.0.0",
            merchant_id=merchant_id, entity_type="RiskEvent", entity_id=risk.risk_event_id,
            payload={"urgency": "P2", "reason_escalated": "amount_over_ceiling"},
        )
        return

    msg = msg_tpl.format(amt=amount_paise // 100) if msg_tpl else None
    cost = 150 if msg else 0
    plan = InterventionPlan(
        diagnosis_id=diag.diagnosis_id, risk_event_id=risk.risk_event_id, action_type=action,
        channel=channel, scheduled_at=when, executed_at=when + timedelta(minutes=2),
        message_content=msg, attribution_window_hours=72, estimated_cost_paise=cost,
        status=enums.PlanStatus.completed,
    )
    session.add(plan)
    await session.flush()
    await write_audit_event(
        session, event_type="ACTION_EXECUTED", actor="execution-layer@1.0.0",
        merchant_id=merchant_id, entity_type="InterventionPlan", entity_id=plan.plan_id,
        payload={"action_type": action.value, "channel": channel.value, "cost_paise": cost},
    )
    if msg:
        session.add(
            Outbox(
                merchant_id=merchant_id, plan_id=plan.plan_id, channel=channel,
                recipient=cust["phone"] if channel != enums.Channel.email else cust["email"],
                body=msg, status=enums.OutboxStatus.sent, cost_paise=cost,
                created_at=when + timedelta(minutes=2),
            )
        )

    if outcome in ("recovered", "unrecovered"):
        recovered = outcome == "recovered"
        conf = random.choice([1.0, 1.0, 0.5]) if recovered else 0.0
        session.add(
            RecoveryRecord(
                plan_id=plan.plan_id, risk_event_id=risk.risk_event_id,
                outcome=enums.RecoveryOutcome.recovered if recovered else enums.RecoveryOutcome.unrecovered,
                recovered_amount_paise=amount_paise if recovered else 0,
                attribution_confidence=conf, recovery_cost_paise=cost,
                recovered_at=risk.resolved_at if recovered else None,
            )
        )
        if recovered:
            await write_audit_event(
                session, event_type="RECOVERY_ATTRIBUTED", actor="outcome-tracker@1.0.0",
                merchant_id=merchant_id, entity_type="RiskEvent", entity_id=risk.risk_event_id,
                payload={"recovered_amount_paise": amount_paise, "attribution_confidence": conf},
            )


async def seed(wipe: bool = True) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        merchant = await get_or_create_demo_merchant(session)
        mid = merchant.merchant_id
        if wipe:
            await _wipe(session)
            merchant = await get_or_create_demo_merchant(session)
            mid = merchant.merchant_id

        customers = _customers(500)

        # --- Bulk successful captures (the "healthy" backdrop) ---
        for _ in range(1500):
            c = random.choice(customers)
            session.add(
                PaymentEvent(
                    merchant_id=mid, gateway=enums.Gateway.razorpay,
                    event_type=enums.EventType.payment_captured,
                    amount_paise=random.randint(20_000, 5_000_000), currency="INR",
                    customer_id=c["id"], customer_phone=c["phone"], customer_email=c["email"],
                    payment_method={"type": "card", "bank": random.choice(BANKS)},
                    received_at=START + timedelta(minutes=random.randint(0, 43_200)),
                )
            )
        await session.commit()

        # --- ~380 at-risk cases across workflows ---
        for _ in range(380):
            c = random.choice(customers)
            root = random.choice(ROOT_CAUSES)
            bank = random.choice(BANKS)
            workflow = CATALOG[root][0]
            amt = (
                random.randint(1_500_000, 25_000_000)
                if workflow == enums.WorkflowType.b2b_receivable
                else random.randint(20_000, 800_000)
            )
            when = START + timedelta(minutes=random.randint(0, 43_200))
            await _make_risk_chain(
                session, mid, c, amt, root, when, bank, random.choice(OUTCOMES)
            )
        await session.commit()

        # --- Scripted HDFC bank-outage window (day -5, 14:00–16:00) ---
        outage_start = (NOW - timedelta(days=5)).replace(hour=14, minute=0, second=0, microsecond=0)
        for _ in range(16):
            c = random.choice(customers)
            when = outage_start + timedelta(minutes=random.randint(0, 120))
            await _make_risk_chain(
                session, mid, c, random.randint(50_000, 900_000), "BANK_OUTAGE", when, "HDFC",
                random.choice(["recovered", "recovered", "in_progress"]),
            )
        await session.commit()

        # --- B2B invoices with an aging spread ---
        for i in range(40):
            c = random.choice(customers)
            days_ago = random.choice([5, 20, 40, 55, 75, 100])
            session.add(
                Invoice(
                    merchant_id=mid, invoice_ref=f"INV-SEED-{1000 + i}", customer_id=c["email"],
                    customer_name=c["name"], customer_email=c["email"], customer_phone=c["phone"],
                    amount_paise=random.randint(500_000, 30_000_000), currency="INR",
                    due_date=(NOW - timedelta(days=days_ago)).date(),
                    status=enums.InvoiceStatus.open, has_active_risk=(days_ago > 30),
                )
            )

        # --- Promises to Pay (mixed states) ---
        for i in range(12):
            c = random.choice(customers)
            st = random.choice(
                [enums.PTPStatus.active, enums.PTPStatus.kept, enums.PTPStatus.broken]
            )
            session.add(
                PromiseToPay(
                    merchant_id=mid, customer_id=c["email"], invoice_id=f"INV-SEED-{1000 + i}",
                    promised_amount_paise=random.randint(500_000, 10_000_000),
                    promised_date=(NOW + timedelta(days=random.randint(-10, 7))).date(),
                    logged_by="ops_seed", status=st,
                )
            )

        # --- DNC entries ---
        for _ in range(6):
            c = random.choice(customers)
            session.add(
                DNCEntry(
                    merchant_id=mid, customer_identifier=hash_identifier(c["phone"]),
                    reason="customer opted out", added_by="ops_seed",
                )
            )

        await session.commit()

    await engine.dispose()
    print("[done] seed complete - open the dashboard and explore, or Fire a live event.")


if __name__ == "__main__":
    asyncio.run(seed(wipe="--keep" not in sys.argv))
