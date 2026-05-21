from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from idea_jam import repo
from idea_jam.auth import COOKIE_NAME, COOKIE_MAX_AGE
from idea_jam.events import bus

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


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    p, is_new = _get_participant_for_request(request)
    ideas = repo.list_ideas_for_participant(p["id"])
    event_state = repo.get_event_state()
    page = request.app.state.templates.TemplateResponse(
        request,
        "attendee_home.html",
        {"participant": p, "ideas": ideas, "event_ended": event_state["ended"]},
    )
    _set_cookie_if_new(page, p, is_new)
    return page


@router.post("/ideas", response_class=HTMLResponse)
async def submit_idea(request: Request, text: str = Form(...)):
    p, is_new = _get_participant_for_request(request)
    text = text.strip()
    if text:
        idea = repo.add_idea(p["id"], text[:500])
        await bus.publish("new_idea", {"id": idea["id"]})
    ideas = repo.list_ideas_for_participant(p["id"])
    page = request.app.state.templates.TemplateResponse(
        request,
        "partials/your_ideas_list.html",
        {"ideas": ideas},
    )
    _set_cookie_if_new(page, p, is_new)
    return page


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
