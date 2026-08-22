"""Bank-level failure-rate aggregator (Redis).

Each payment (success or failure) to an issuing bank is recorded in per-minute
counters. The rolling 1-hour failure rate is a proxy for a bank-side outage
(blueprint §9.1 / §9). Pure Redis — no external dependency.

Keys (all TTL'd ~90 min so they self-expire):
    aria:bankfail:{merchant}:{bank}:{minute}:fail  -> count
    aria:bankfail:{merchant}:{bank}:{minute}:total -> count
"""

from __future__ import annotations

from app.core.redis import get_redis

_TTL_SECONDS = 90 * 60
_WINDOW_MINUTES = 60


def _epoch_minute(ts: float) -> int:
    return int(ts // 60)


async def record_payment(merchant_id: str, bank: str, *, failed: bool, now_epoch: float) -> None:
    """Increment the per-minute total (and fail) counters for a bank."""
    if not bank:
        return
    r = get_redis()
    minute = _epoch_minute(now_epoch)
    base = f"aria:bankfail:{merchant_id}:{bank.lower()}:{minute}"
    pipe = r.pipeline()
    pipe.incr(f"{base}:total")
    pipe.expire(f"{base}:total", _TTL_SECONDS)
    if failed:
        pipe.incr(f"{base}:fail")
        pipe.expire(f"{base}:fail", _TTL_SECONDS)
    await pipe.execute()


async def failure_rate_1h(merchant_id: str, bank: str, *, now_epoch: float) -> tuple[float, int]:
    """Return (failure_rate, total_count) over the last hour for a bank."""
    if not bank:
        return 0.0, 0
    r = get_redis()
    current = _epoch_minute(now_epoch)
    fail_keys, total_keys = [], []
    for m in range(current - _WINDOW_MINUTES + 1, current + 1):
        base = f"aria:bankfail:{merchant_id}:{bank.lower()}:{m}"
        fail_keys.append(f"{base}:fail")
        total_keys.append(f"{base}:total")

    fails = await r.mget(fail_keys)
    totals = await r.mget(total_keys)
    total = sum(int(x) for x in totals if x)
    fail = sum(int(x) for x in fails if x)
    if total == 0:
        return 0.0, 0
    return fail / total, total
