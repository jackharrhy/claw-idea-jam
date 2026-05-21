from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Protocol

from anthropic import Anthropic

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
MODEL = "claude-sonnet-4-5"


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


class LLMClient(Protocol):
    async def cluster(self, ideas: list[dict]) -> list[dict]: ...
    async def starter_prompt(self, idea_text: str) -> str: ...


class AnthropicClient:
    def __init__(self, api_key: str | None = None, model: str = MODEL) -> None:
        self._client = Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self._model = model

    async def cluster(self, ideas: list[dict]) -> list[dict]:
        template = _load_prompt("cluster.md")
        ideas_json = json.dumps([{"id": i["id"], "text": i["text"]} for i in ideas], ensure_ascii=False)
        prompt = template.replace("{{ ideas_json }}", ideas_json)
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text  # type: ignore[union-attr]
        parsed = _extract_json(text)
        themes = parsed["themes"]
        # Sanity check: every input id is assigned exactly once
        assigned: set[str] = set()
        input_ids = {i["id"] for i in ideas}
        for t in themes:
            for iid in t["idea_ids"]:
                if iid in assigned:
                    raise ValueError(f"id {iid} assigned to multiple themes")
                if iid not in input_ids:
                    raise ValueError(f"id {iid} not in input")
                assigned.add(iid)
        missing = input_ids - assigned
        if missing:
            raise ValueError(f"unassigned ideas: {missing}")
        return themes

    async def starter_prompt(self, idea_text: str) -> str:
        template = _load_prompt("starter.md")
        prompt = template.replace("{{ idea_text }}", idea_text)
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()  # type: ignore[union-attr]


def _extract_json(text: str) -> dict:
    """Extract the first JSON object from a model response."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in response: {text[:200]}")
    return json.loads(text[start:end + 1])


class FakeLLMClient:
    """Test/dev double. Cluster returns naive partition; starter returns stub."""

    async def cluster(self, ideas: list[dict]) -> list[dict]:
        if not ideas:
            return []
        # Two themes: first half "alpha", second half "beta"
        mid = max(1, len(ideas) // 2)
        return [
            {"name": "alpha", "idea_ids": [i["id"] for i in ideas[:mid]]},
            {"name": "beta", "idea_ids": [i["id"] for i in ideas[mid:]]},
        ]

    async def starter_prompt(self, idea_text: str) -> str:
        return f"Try this with Claude Code: {idea_text}. Start by mocking a small example."
