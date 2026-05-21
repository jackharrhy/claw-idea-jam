import asyncio
import json
import pytest
from idea_jam.events import EventBus


@pytest.mark.asyncio
async def test_pub_sub_delivers():
    b = EventBus()
    q = b.subscribe()
    await b.publish("hello", {"x": 1})
    msg = await asyncio.wait_for(q.get(), timeout=1.0)
    parsed = json.loads(msg)
    assert parsed == {"type": "hello", "data": {"x": 1}}


@pytest.mark.asyncio
async def test_unsubscribe_no_more_messages():
    b = EventBus()
    q = b.subscribe()
    b.unsubscribe(q)
    await b.publish("hello", {})
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(q.get(), timeout=0.1)
