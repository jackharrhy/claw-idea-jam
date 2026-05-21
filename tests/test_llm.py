import pytest
from idea_jam.llm import FakeLLMClient, _extract_json


def test_extract_json_clean():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_with_preamble():
    assert _extract_json('Sure thing! Here:\n{"a": 1}\nLet me know.') == {"a": 1}


def test_extract_json_missing():
    with pytest.raises(ValueError):
        _extract_json("no braces here")


@pytest.mark.asyncio
async def test_fake_cluster_partitions_all():
    fake = FakeLLMClient()
    ideas = [{"id": str(i), "text": f"idea {i}"} for i in range(6)]
    themes = await fake.cluster(ideas)
    flat = [iid for t in themes for iid in t["idea_ids"]]
    assert sorted(flat) == sorted([i["id"] for i in ideas])


@pytest.mark.asyncio
async def test_fake_starter_prompt():
    fake = FakeLLMClient()
    out = await fake.starter_prompt("automate my email")
    assert "automate my email" in out
