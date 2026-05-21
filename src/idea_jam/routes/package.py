import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from idea_jam import repo
from idea_jam.auth import COOKIE_NAME

router = APIRouter()


@router.get("/package", response_class=HTMLResponse)
async def package(request: Request):
    pid = request.cookies.get(COOKIE_NAME)
    if not pid:
        raise HTTPException(404)
    p = repo.get_participant(pid)
    if not p:
        raise HTTPException(404)
    state = repo.get_event_state()
    if not state["ended"]:
        raise HTTPException(404)
    ideas = repo.list_ideas_for_participant(pid)
    return request.app.state.templates.TemplateResponse(
        request,
        "package.html",
        {"participant": p, "ideas": ideas, "ideas_json": json.dumps(ideas)},
    )
