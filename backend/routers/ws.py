"""
Single live WebSocket channel. Subscribes to the shared state pub/sub and
forwards every event (trade executions, simulation throughput, kill-switch
toggles, resets) to connected dashboard clients in real time.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.state import store

router = APIRouter(tags=["websocket"])
logger = logging.getLogger("athena.ws")


@router.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    await websocket.accept()
    sub_task: asyncio.Task | None = None

    async def forward():
        async for event in store.subscribe():
            await websocket.send_json(event)

    try:
        sub_task = asyncio.create_task(forward())
        while True:
            # Drain any client pings/messages; connection stays open until client disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WS client disconnected")
    finally:
        if sub_task:
            sub_task.cancel()
