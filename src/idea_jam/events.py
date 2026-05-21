import asyncio
import json
from typing import AsyncIterator


class EventBus:
    """In-process pub/sub via per-subscriber asyncio.Queue."""

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[str]] = []

    def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def publish(self, event_type: str, payload: dict) -> None:
        msg = json.dumps({"type": event_type, "data": payload})
        dead: list[asyncio.Queue[str]] = []
        for q in self._subscribers:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self.unsubscribe(q)


bus = EventBus()


async def event_stream(q: asyncio.Queue[str]) -> AsyncIterator[dict]:
    try:
        while True:
            msg = await q.get()
            yield {"event": "message", "data": msg}
    finally:
        bus.unsubscribe(q)
