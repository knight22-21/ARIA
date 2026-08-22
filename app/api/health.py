"""Health & readiness endpoints."""

from fastapi import APIRouter
from sqlalchemy import text

from app import __version__
from app.core.config import settings
from app.core.db import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness: the API process is up."""
    return {"status": "ok", "service": "aria", "version": __version__}


@router.get("/health/ready")
async def ready() -> dict:
    """Readiness: dependencies (Postgres, Redis) are reachable."""
    checks: dict[str, str] = {}

    # Postgres
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001 — report, don't crash the probe
        checks["postgres"] = f"error: {type(exc).__name__}"

    # Redis
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.redis_url)
        await client.ping()
        await client.aclose()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {type(exc).__name__}"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ready" if all_ok else "degraded", "checks": checks}
