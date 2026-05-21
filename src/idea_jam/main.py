from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from idea_jam.db import init_db
from idea_jam.llm import AnthropicClient, FakeLLMClient
from idea_jam.routes import attendee, moderator, package


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _make_llm():
    if os.environ.get("IDEA_JAM_FAKE_LLM") == "1":
        return FakeLLMClient()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return FakeLLMClient()
    return AnthropicClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.templates = templates
    app.state.llm = _make_llm()
    yield


app = FastAPI(title="Idea Jam", lifespan=lifespan)
app.include_router(attendee.router)
app.include_router(moderator.router)
app.include_router(package.router)


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}
