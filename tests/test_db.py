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
    # The participants table should exist and be empty.
    with fresh_db.engine.begin() as conn:
        rows = conn.execute(fresh_db.participants.select()).all()
    assert rows == []


def test_init_db_idempotent(fresh_db):
    fresh_db.init_db()  # second call must not error
    with fresh_db.engine.begin() as conn:
        rows = conn.execute(fresh_db.participants.select()).all()
    assert rows == []
