import json

from fastapi import APIRouter, Body, Form, Path, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sse_starlette.sse import EventSourceResponse

from idea_jam import repo
from idea_jam.auth import (
    MOD_COOKIE_NAME,
    MOD_COOKIE_MAX_AGE,
    check_moderator_password,
    require_moderator,
)
from idea_jam.events import bus, event_stream

router = APIRouter(prefix="/m")


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    # If already authenticated, send to dashboard.
    cookie_val = request.cookies.get(MOD_COOKIE_NAME)
    if cookie_val and check_moderator_password(cookie_val):
        return RedirectResponse("/m/dashboard", status_code=303)
    return request.app.state.templates.TemplateResponse(
        request,
        "moderator_login.html",
        {},
    )


@router.post("/login")
async def login(request: Request, token: str = Form(...)):
    if not check_moderator_password(token):
        page = request.app.state.templates.TemplateResponse(
            request,
            "moderator_login.html",
            {"error": "invalid token"},
            status_code=200,
        )
        return page
    resp = RedirectResponse("/m/dashboard", status_code=303)
    resp.set_cookie(
        key=MOD_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=MOD_COOKIE_MAX_AGE,
    )
    return resp


@router.post("/logout")
async def logout(request: Request):
    resp = RedirectResponse("/m", status_code=303)
    resp.delete_cookie(MOD_COOKIE_NAME)
    return resp


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    require_moderator(request)
    ideas = repo.list_ideas_with_participant_name()
    themes = repo.list_themes()
    return request.app.state.templates.TemplateResponse(
        request,
        "moderator_dashboard.html",
        {"ideas": ideas, "themes": themes},
    )


@router.get("/events")
async def events(request: Request):
    require_moderator(request)
    q = bus.subscribe()
    return EventSourceResponse(event_stream(q))


@router.post("/themes")
async def create_theme(request: Request, payload: dict = Body(...)):
    require_moderator(request)
    t = repo.create_theme(payload["name"])
    await bus.publish("themes_changed", {})
    return JSONResponse(t)


@router.patch("/themes/{theme_id}")
async def patch_theme(
    request: Request,
    theme_id: str = Path(...),
    name: str | None = Form(None),
    position: int | None = Form(None),
):
    require_moderator(request)
    if name is not None:
        repo.rename_theme(theme_id, name)
    if position is not None:
        repo.reorder_theme(theme_id, position)
    await bus.publish("themes_changed", {})
    return {"ok": True}


@router.delete("/themes/{theme_id}")
async def delete_theme(request: Request, theme_id: str = Path(...)):
    require_moderator(request)
    repo.delete_theme(theme_id)
    await bus.publish("themes_changed", {})
    return {"ok": True}


@router.post("/ideas/{idea_id}/move")
async def move_idea(request: Request, idea_id: str = Path(...), payload: dict = Body(...)):
    require_moderator(request)
    theme_id = payload.get("theme_id") or None
    pos = payload.get("position")
    repo.move_idea(idea_id, theme_id, int(pos) if pos is not None else None)
    await bus.publish("themes_changed", {})
    return {"ok": True}


@router.post("/ideas/{idea_id}/star")
async def star(request: Request, idea_id: str = Path(...)):
    require_moderator(request)
    new = repo.toggle_star(idea_id)
    await bus.publish("themes_changed", {})
    return {"starred": new}


@router.post("/auto-cluster")
async def auto_cluster(request: Request):
    require_moderator(request)
    llm = request.app.state.llm
    all_ideas = repo.list_all_ideas()
    unclustered = [i for i in all_ideas if i["theme_id"] is None]
    if not unclustered:
        return {"ok": True, "themes_created": 0}
    try:
        proposed = await llm.cluster(unclustered)
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": f"clustering failed: {type(e).__name__}: {e}"},
            status_code=422,
        )
    created = 0
    for theme in proposed:
        t = repo.create_theme(theme["name"])
        created += 1
        for pos, iid in enumerate(theme["idea_ids"]):
            repo.move_idea(iid, t["id"], pos)
    await bus.publish("themes_changed", {})
    return {"ok": True, "themes_created": created}


@router.post("/wipe")
async def wipe(request: Request):
    require_moderator(request)
    repo.wipe_all()
    await bus.publish("themes_changed", {})
    return {"ok": True}


@router.get("/reveal", response_class=HTMLResponse)
async def reveal(request: Request):
    require_moderator(request)
    themes = repo.list_themes()
    all_ideas = repo.list_ideas_with_participant_name()
    by_theme = []
    for t in themes:
        starred = [i for i in all_ideas if i["theme_id"] == t["id"] and i["starred"]]
        by_theme.append({
            "id": t["id"],
            "name": t["name"],
            "ideas": [{"text": i["text"], "display_name": i["display_name"]} for i in starred],
        })
    return request.app.state.templates.TemplateResponse(
        request,
        "moderator_reveal.html",
        {"themes": by_theme, "themes_json": json.dumps(by_theme)},
    )


@router.get("/export", response_class=HTMLResponse)
async def export(request: Request):
    require_moderator(request)
    from sqlalchemy import select
    from idea_jam.db import engine, participants, ideas as ideas_t, themes as themes_t

    # Join everything in one query so we have name + email per idea + theme name.
    stmt = (
        select(
            ideas_t.c.id,
            ideas_t.c.text,
            ideas_t.c.starred,
            ideas_t.c.created_at,
            ideas_t.c.theme_id,
            themes_t.c.name.label("theme_name"),
            themes_t.c.position.label("theme_position"),
            participants.c.id.label("participant_id"),
            participants.c.display_name,
            participants.c.email,
        )
        .select_from(
            ideas_t.join(participants, ideas_t.c.participant_id == participants.c.id)
            .outerjoin(themes_t, ideas_t.c.theme_id == themes_t.c.id)
        )
        .order_by(themes_t.c.position.asc().nulls_last(), ideas_t.c.created_at.asc())
    )
    with engine.begin() as conn:
        rows = [dict(r._mapping) for r in conn.execute(stmt).all()]

    # Group by theme. None bucket goes last.
    grouped: dict[str | None, list[dict]] = {}
    theme_order: list[str | None] = []
    for r in rows:
        key = r["theme_id"]
        if key not in grouped:
            grouped[key] = []
            theme_order.append(key)
        grouped[key].append(r)

    # Always show "Unclustered" last, even if it has the lowest theme_position (which is None).
    if None in theme_order:
        theme_order = [k for k in theme_order if k is not None] + [None]

    # Build markdown.
    from datetime import datetime, timezone
    lines: list[str] = []
    lines.append("# idea jam export")
    lines.append("")
    lines.append(f"_exported {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_")
    lines.append("")

    for theme_id in theme_order:
        theme_rows = grouped[theme_id]
        theme_name = theme_rows[0]["theme_name"] if theme_id is not None else "Unclustered"
        lines.append(f"## {theme_name}")
        lines.append("")
        for r in theme_rows:
            mark = "★ " if r["starred"] else ""
            text = r["text"].replace("\n", " ").strip()
            who = r["display_name"]
            email = f" <{r['email']}>" if r["email"] else ""
            lines.append(f"- {mark}{text} _({who}{email})_")
        lines.append("")

    # Participants section with emails for follow-up.
    p_stmt = (
        select(participants.c.display_name, participants.c.email)
        .where(participants.c.email.is_not(None))
        .order_by(participants.c.display_name)
    )
    with engine.begin() as conn:
        with_emails = [dict(r._mapping) for r in conn.execute(p_stmt).all()]

    if with_emails:
        lines.append("## Participants with emails (for follow-up)")
        lines.append("")
        for p in with_emails:
            lines.append(f"- {p['display_name']} <{p['email']}>")
        lines.append("")

    markdown = "\n".join(lines)

    return request.app.state.templates.TemplateResponse(
        request,
        "moderator_export.html",
        {"markdown": markdown},
    )
