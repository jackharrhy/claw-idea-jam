from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from idea_jam import repo
from idea_jam.auth import COOKIE_NAME, COOKIE_MAX_AGE
from idea_jam.events import bus
from idea_jam.names import generate_display_name

router = APIRouter()


def _get_participant_for_request(request: Request) -> tuple[dict, bool]:
    """Return (participant, is_new). Caller is responsible for setting the cookie if is_new."""
    pid = request.cookies.get(COOKIE_NAME)
    if pid:
        existing = repo.get_participant(pid)
        if existing:
            return existing, False
    return repo.create_participant(), True


def _set_cookie_if_new(response, participant: dict, is_new: bool) -> None:
    if is_new:
        response.set_cookie(
            key=COOKIE_NAME, value=participant["id"],
            httponly=True, samesite="lax", max_age=COOKIE_MAX_AGE,
        )


def _set_participant_cookie(response, participant: dict) -> None:
    response.set_cookie(
        key=COOKIE_NAME, value=participant["id"],
        httponly=True, samesite="lax", max_age=COOKIE_MAX_AGE,
    )


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    pid = request.cookies.get(COOKIE_NAME)
    p = repo.get_participant(pid) if pid else None
    if not p:
        # No cookie or stale cookie -> show name entry screen, do NOT create.
        return request.app.state.templates.TemplateResponse(
            request,
            "attendee_name_entry.html",
            {},
        )
    ideas = repo.list_ideas_for_participant(p["id"])
    event_state = repo.get_event_state()
    return request.app.state.templates.TemplateResponse(
        request,
        "attendee_home.html",
        {"participant": p, "ideas": ideas, "event_ended": event_state["ended"]},
    )


@router.post("/me/claim-name")
async def claim_name(request: Request, display_name: str = Form(...)):
    name = display_name.strip()[:64]
    if not name:
        name = generate_display_name()
    p = repo.create_participant_with_name(name)
    resp = RedirectResponse("/", status_code=303)
    _set_participant_cookie(resp, p)
    return resp


@router.post("/me/random-name")
async def random_name(request: Request):
    p = repo.create_participant()
    resp = RedirectResponse("/", status_code=303)
    _set_participant_cookie(resp, p)
    return resp


@router.post("/ideas", response_class=HTMLResponse)
async def submit_idea(request: Request, text: str = Form(...)):
    pid = request.cookies.get(COOKIE_NAME)
    p = repo.get_participant(pid) if pid else None
    if not p:
        raise HTTPException(status_code=400, detail="no participant cookie; visit / first")
    text = text.strip()
    if text:
        idea = repo.add_idea(p["id"], text[:500])
        await bus.publish("new_idea", {"id": idea["id"]})
    ideas = repo.list_ideas_for_participant(p["id"])
    return request.app.state.templates.TemplateResponse(
        request,
        "partials/your_ideas_list.html",
        {"ideas": ideas},
    )


@router.delete("/ideas/{idea_id}", response_class=HTMLResponse)
async def delete_own_idea(request: Request, idea_id: str):
    pid = request.cookies.get(COOKIE_NAME)
    if not pid:
        raise HTTPException(404)
    existing = repo.get_idea(idea_id)
    if not existing or existing["participant_id"] != pid:
        raise HTTPException(404)
    repo.delete_idea(idea_id)
    await bus.publish("idea_deleted", {"id": idea_id})
    ideas = repo.list_ideas_for_participant(pid)
    return request.app.state.templates.TemplateResponse(
        request,
        "partials/your_ideas_list.html",
        {"ideas": ideas},
    )


@router.post("/ideas/{idea_id}/edit", response_class=HTMLResponse)
async def edit_own_idea(request: Request, idea_id: str, text: str = Form(...)):
    pid = request.cookies.get(COOKIE_NAME)
    if not pid:
        raise HTTPException(404)
    existing = repo.get_idea(idea_id)
    if not existing or existing["participant_id"] != pid:
        raise HTTPException(404)
    new_text = text.strip()[:500]
    if not new_text:
        raise HTTPException(400, detail="empty text")
    repo.update_idea_text(idea_id, new_text)
    await bus.publish("idea_edited", {"id": idea_id})
    ideas = repo.list_ideas_for_participant(pid)
    return request.app.state.templates.TemplateResponse(
        request,
        "partials/your_ideas_list.html",
        {"ideas": ideas},
    )


@router.post("/me/regenerate-name", response_class=HTMLResponse)
async def regen_name(request: Request):
    p, is_new = _get_participant_for_request(request)
    new_name = repo.regenerate_participant_name(p["id"])
    from fastapi.responses import HTMLResponse as HR
    resp = HR(new_name)
    _set_cookie_if_new(resp, p, is_new)
    return resp


@router.post("/me/rename", response_class=HTMLResponse)
async def rename(request: Request, display_name: str = Form(...)):
    p, is_new = _get_participant_for_request(request)
    new_name = display_name.strip()[:64] or p["display_name"]
    repo.rename_participant(p["id"], new_name)
    from fastapi.responses import HTMLResponse as HR
    resp = HR(new_name)
    _set_cookie_if_new(resp, p, is_new)
    return resp
