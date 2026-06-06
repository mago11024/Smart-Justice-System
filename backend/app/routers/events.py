"""SSE 端点 — async generator 产出 text/event-stream"""
import json
import time
import asyncio
import queue

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.services.sse_manager import sse_manager

router = APIRouter(prefix="/api", tags=["events"])

HEARTBEAT_INTERVAL = 25  # 秒，低于代理超时（通常 30-60s）


@router.get("/events")
async def event_stream(request: Request):
    q = sse_manager.register()
    last_event_time = time.time()

    async def generate():
        nonlocal last_event_time
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = q.get_nowait()
                    event = json.loads(payload)
                    yield (
                        f"event: {event['type']}\n"
                        f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
                    )
                    last_event_time = time.time()
                except queue.Empty:
                    now = time.time()
                    if now - last_event_time >= HEARTBEAT_INTERVAL:
                        yield f"event: heartbeat\ndata: {json.dumps({'time': now})}\n\n"
                        last_event_time = now
                    await asyncio.sleep(1)
        finally:
            sse_manager.unregister(q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
