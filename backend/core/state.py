"""
ATHENA shared state.

Wraps Redis for cross-process shared state (trade history, agent logs,
risk status, live simulation stats) with pub/sub for WebSocket fan-out.
Falls back to an in-memory store automatically if Redis isn't reachable,
so `uvicorn main:app` works standalone with zero infra for quick testing.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import deque
from typing import Any

logger = logging.getLogger("athena.state")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CHANNEL = "athena:events"
MAX_HISTORY = 5000


class _MemoryBackend:
    """Fallback store — same surface as the Redis client we need."""

    def __init__(self):
        self._kv: dict[str, Any] = {}
        self._lists: dict[str, deque] = {}
        self._subscribers: list[asyncio.Queue] = []

    async def set_json(self, key: str, value: Any):
        self._kv[key] = value

    async def get_json(self, key: str, default=None):
        return self._kv.get(key, default)

    async def push_list(self, key: str, value: Any, max_len: int = MAX_HISTORY):
        if key not in self._lists:
            self._lists[key] = deque(maxlen=max_len)
        self._lists[key].append(value)

    async def get_list(self, key: str, limit: int = 200) -> list:
        return list(self._lists.get(key, []))[-limit:]

    async def delete(self, key: str):
        self._kv.pop(key, None)
        self._lists.pop(key, None)

    async def publish(self, channel: str, message: dict):
        payload = json.dumps(message)
        for q in self._subscribers:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)


class StateStore:
    """Public API used by routers/agents. Backed by Redis if available, else memory."""

    def __init__(self):
        self._redis = None
        self._memory = _MemoryBackend()
        self._using_redis = False
        self._pubsub_task: asyncio.Task | None = None

    async def connect(self):
        try:
            import redis.asyncio as aioredis  # lazy import — optional dependency at runtime
            client = aioredis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=1.5)
            await client.ping()
            self._redis = client
            self._using_redis = True
            logger.info("StateStore: connected to Redis at %s", REDIS_URL)
        except Exception as exc:  # noqa: BLE001 — any failure -> graceful fallback
            self._redis = None
            self._using_redis = False
            logger.warning("StateStore: Redis unavailable (%s) — using in-memory store. "
                            "Fine for local dev; use Redis in production for multi-worker deployments.", exc)

    @property
    def backend(self) -> str:
        return "redis" if self._using_redis else "memory"

    async def set_json(self, key: str, value: Any):
        if self._using_redis:
            await self._redis.set(key, json.dumps(value))
        else:
            await self._memory.set_json(key, value)

    async def get_json(self, key: str, default=None):
        if self._using_redis:
            raw = await self._redis.get(key)
            return json.loads(raw) if raw else default
        return await self._memory.get_json(key, default)

    async def push_list(self, key: str, value: Any, max_len: int = MAX_HISTORY):
        value = {**value, "_ts": value.get("_ts", time.time())}
        if self._using_redis:
            await self._redis.rpush(key, json.dumps(value))
            await self._redis.ltrim(key, -max_len, -1)
        else:
            await self._memory.push_list(key, value, max_len)

    async def get_list(self, key: str, limit: int = 200) -> list:
        if self._using_redis:
            raw = await self._redis.lrange(key, -limit, -1)
            return [json.loads(r) for r in raw]
        return await self._memory.get_list(key, limit)

    async def delete_key(self, key: str):
        if self._using_redis:
            await self._redis.delete(key)
        else:
            await self._memory.delete(key)

    async def publish(self, message: dict):
        message = {**message, "_ts": message.get("_ts", time.time())}
        if self._using_redis:
            await self._redis.publish(CHANNEL, json.dumps(message))
        else:
            await self._memory.publish(CHANNEL, message)

    async def subscribe(self):
        """Async generator yielding JSON-decoded events. Works for both backends."""
        if self._using_redis:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(CHANNEL)
            try:
                async for msg in pubsub.listen():
                    if msg["type"] == "message":
                        yield json.loads(msg["data"])
            finally:
                await pubsub.unsubscribe(CHANNEL)
        else:
            q = self._memory.subscribe()
            try:
                while True:
                    payload = await q.get()
                    yield json.loads(payload)
            finally:
                self._memory.unsubscribe(q)


# Single shared instance used across the app
store = StateStore()
