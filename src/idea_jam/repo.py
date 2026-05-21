from datetime import datetime, timezone
from sqlalchemy import select, update, delete, func
from idea_jam.db import engine, participants, themes, ideas, event_state
from idea_jam.names import generate_display_name, new_uuid


def _now() -> datetime:
    return datetime.now(timezone.utc)


# Participants

def create_participant() -> dict:
    pid = new_uuid()
    name = generate_display_name()
    with engine.begin() as conn:
        conn.execute(participants.insert().values(id=pid, display_name=name, created_at=_now()))
    return {"id": pid, "display_name": name}


def create_participant_with_name(name: str) -> dict:
    pid = new_uuid()
    with engine.begin() as conn:
        conn.execute(participants.insert().values(id=pid, display_name=name, created_at=_now()))
    return {"id": pid, "display_name": name}


def get_participant(pid: str) -> dict | None:
    with engine.begin() as conn:
        row = conn.execute(participants.select().where(participants.c.id == pid)).first()
    return dict(row._mapping) if row else None


def rename_participant(pid: str, new_name: str) -> None:
    with engine.begin() as conn:
        conn.execute(update(participants).where(participants.c.id == pid).values(display_name=new_name))


def regenerate_participant_name(pid: str) -> str:
    new_name = generate_display_name()
    rename_participant(pid, new_name)
    return new_name


# Ideas

def add_idea(participant_id: str, text: str) -> dict:
    iid = new_uuid()
    with engine.begin() as conn:
        conn.execute(ideas.insert().values(
            id=iid, participant_id=participant_id, text=text,
            theme_id=None, starred=True, position_in_theme=None,
            starter_prompt=None, created_at=_now(),
        ))
        row = conn.execute(ideas.select().where(ideas.c.id == iid)).first()
    return dict(row._mapping)


def get_idea(idea_id: str) -> dict | None:
    with engine.begin() as conn:
        row = conn.execute(ideas.select().where(ideas.c.id == idea_id)).first()
    return dict(row._mapping) if row else None


def delete_idea(idea_id: str) -> None:
    with engine.begin() as conn:
        conn.execute(delete(ideas).where(ideas.c.id == idea_id))


def update_idea_text(idea_id: str, text: str) -> None:
    with engine.begin() as conn:
        conn.execute(update(ideas).where(ideas.c.id == idea_id).values(text=text))


def list_ideas_for_participant(participant_id: str) -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            ideas.select().where(ideas.c.participant_id == participant_id).order_by(ideas.c.created_at.desc())
        ).all()
    return [dict(r._mapping) for r in rows]


def list_all_ideas() -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(ideas.select().order_by(ideas.c.created_at.desc())).all()
    return [dict(r._mapping) for r in rows]


def list_ideas_with_participant_name() -> list[dict]:
    j = ideas.join(participants, ideas.c.participant_id == participants.c.id)
    stmt = select(ideas, participants.c.display_name).select_from(j).order_by(ideas.c.created_at.desc())
    with engine.begin() as conn:
        rows = conn.execute(stmt).all()
    return [dict(r._mapping) for r in rows]


def move_idea(idea_id: str, theme_id: str | None, position: int | None) -> None:
    with engine.begin() as conn:
        conn.execute(update(ideas).where(ideas.c.id == idea_id).values(
            theme_id=theme_id, position_in_theme=position,
        ))


def toggle_star(idea_id: str) -> bool:
    with engine.begin() as conn:
        row = conn.execute(select(ideas.c.starred).where(ideas.c.id == idea_id)).first()
        if row is None:
            raise ValueError(f"idea {idea_id} not found")
        new_value = not row.starred
        conn.execute(update(ideas).where(ideas.c.id == idea_id).values(starred=new_value))
    return new_value


def set_starter_prompt(idea_id: str, prompt: str) -> None:
    with engine.begin() as conn:
        conn.execute(update(ideas).where(ideas.c.id == idea_id).values(starter_prompt=prompt))


# Themes

def create_theme(name: str) -> dict:
    tid = new_uuid()
    with engine.begin() as conn:
        max_pos = conn.execute(select(func.coalesce(func.max(themes.c.position), -1))).scalar_one()
        conn.execute(themes.insert().values(id=tid, name=name, position=max_pos + 1, created_at=_now()))
        row = conn.execute(themes.select().where(themes.c.id == tid)).first()
    return dict(row._mapping)


def list_themes() -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(themes.select().order_by(themes.c.position)).all()
    return [dict(r._mapping) for r in rows]


def rename_theme(tid: str, name: str) -> None:
    with engine.begin() as conn:
        conn.execute(update(themes).where(themes.c.id == tid).values(name=name))


def reorder_theme(tid: str, position: int) -> None:
    with engine.begin() as conn:
        conn.execute(update(themes).where(themes.c.id == tid).values(position=position))


def delete_theme(tid: str) -> None:
    with engine.begin() as conn:
        conn.execute(update(ideas).where(ideas.c.theme_id == tid).values(theme_id=None, position_in_theme=None))
        conn.execute(delete(themes).where(themes.c.id == tid))


# Event state

def get_event_state() -> dict:
    with engine.begin() as conn:
        row = conn.execute(event_state.select().where(event_state.c.id == 1)).first()
    return dict(row._mapping)


def end_event() -> None:
    with engine.begin() as conn:
        conn.execute(update(event_state).where(event_state.c.id == 1).values(ended=True))


def set_packages_status(status: str) -> None:
    assert status in ("not_started", "generating", "complete")
    with engine.begin() as conn:
        conn.execute(update(event_state).where(event_state.c.id == 1).values(packages_status=status))
