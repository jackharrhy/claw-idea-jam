import importlib
import pytest


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    # Force re-import so the engine picks up the new URL
    import idea_jam.db as db
    importlib.reload(db)
    db.init_db()
    return db


def test_init_db_creates_tables(fresh_db):
    with fresh_db.engine.begin() as conn:
        rows = conn.execute(fresh_db.event_state.select()).all()
    assert len(rows) == 1
    assert rows[0].id == 1
    assert rows[0].ended is False


def test_init_db_idempotent(fresh_db):
    fresh_db.init_db()  # second call must not error or duplicate event_state
    with fresh_db.engine.begin() as conn:
        rows = conn.execute(fresh_db.event_state.select()).all()
    assert len(rows) == 1
