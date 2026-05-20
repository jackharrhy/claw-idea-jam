import os
from datetime import datetime
from sqlalchemy import (
    create_engine, MetaData, Table, Column, String, Integer, Boolean,
    DateTime, ForeignKey, Text, event, text,
)
from sqlalchemy.engine import Engine

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./idea_jam.db")

engine: Engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    future=True,
)


@event.listens_for(Engine, "connect")
def _enable_sqlite_wal(dbapi_conn, _):  # type: ignore[no-untyped-def]
    if "sqlite" in str(engine.url):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


metadata = MetaData()

participants = Table(
    "participants", metadata,
    Column("id", String, primary_key=True),
    Column("display_name", String, nullable=False),
    Column("created_at", DateTime, nullable=False),
)

themes = Table(
    "themes", metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("position", Integer, nullable=False),
    Column("created_at", DateTime, nullable=False),
)

ideas = Table(
    "ideas", metadata,
    Column("id", String, primary_key=True),
    Column("participant_id", String, ForeignKey("participants.id"), nullable=False),
    Column("text", String, nullable=False),
    Column("theme_id", String, ForeignKey("themes.id"), nullable=True),
    Column("starred", Boolean, nullable=False, default=False),
    Column("position_in_theme", Integer, nullable=True),
    Column("starter_prompt", Text, nullable=True),
    Column("created_at", DateTime, nullable=False),
)

event_state = Table(
    "event_state", metadata,
    Column("id", Integer, primary_key=True),
    Column("ended", Boolean, nullable=False, default=False),
    Column("packages_status", String, nullable=False, default="not_started"),
)


def init_db() -> None:
    metadata.create_all(engine)
    with engine.begin() as conn:
        existing = conn.execute(text("SELECT id FROM event_state WHERE id=1")).first()
        if existing is None:
            conn.execute(event_state.insert().values(id=1, ended=False, packages_status="not_started"))
