"""Server-Sent Events — live pipeline stream.

The dashboard opens one persistent connection here; every audit event published to
Redis (by ``write_audit_event``) is pushed to the browser the instant it happens, so
pipeline steps appear live, one by one, as the agent executes them.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.audit import EVENT_CHANNEL
from app.core.redis import get_redis

router = APIRouter(prefix="/v1", tags=["stream"])


async def _event_generator() -> AsyncGenerator[str, None]:
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(EVENT_CHANNEL)
    try:
        yield ": connected\n\n"
        while True:
            # Block up to 15s for a message; otherwise emit a heartbeat comment so the
            # connection stays alive and the generator notices client disconnects.
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
            if msg and msg.get("type") == "message":
                yield f"data: {msg['data']}\n\n"
            else:
                yield ": ping\n\n"
    finally:
        try:
            await pubsub.unsubscribe(EVENT_CHANNEL)
            await pubsub.aclose()
        except Exception:  # noqa: BLE001
            pass


@router.get("/stream")
async def stream() -> StreamingResponse:
    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering
        },
    )
