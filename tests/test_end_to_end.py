import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'e2e.db'}")
    monkeypatch.setenv("MODERATOR_TOKEN", "test-token")
    monkeypatch.setenv("IDEA_JAM_FAKE_LLM", "1")
    # Reload modules so env vars apply
    import idea_jam.db, idea_jam.repo
    import idea_jam.routes.attendee, idea_jam.routes.moderator, idea_jam.routes.package
    import idea_jam.main
    importlib.reload(idea_jam.db)
    importlib.reload(idea_jam.repo)
    importlib.reload(idea_jam.routes.attendee)
    importlib.reload(idea_jam.routes.moderator)
    importlib.reload(idea_jam.routes.package)
    importlib.reload(idea_jam.main)
    with TestClient(idea_jam.main.app) as c:
        yield c


def test_full_flow(client):
    # Attendee 1 lands, gets a cookie
    r = client.get("/")
    assert r.status_code == 200
    a1_cookie = client.cookies.get("ij_pid")
    assert a1_cookie

    # Attendee 1 submits two ideas
    r = client.post("/ideas", data={"text": "automate my email triage"})
    assert r.status_code == 200
    r = client.post("/ideas", data={"text": "summarise my standup notes"})
    assert r.status_code == 200

    # Attendee 2 (fresh client cookies)
    client.cookies.clear()
    r = client.get("/")
    assert r.status_code == 200
    r = client.post("/ideas", data={"text": "watch my deploys and alert me"})
    assert r.status_code == 200

    # Moderator dashboard reachable with right token
    r = client.get("/m/test-token")
    assert r.status_code == 200
    assert "automate my email triage" in r.text

    # Wrong token returns 404 (don't leak existence)
    r = client.get("/m/wrong-token")
    assert r.status_code == 404

    # Auto-cluster
    r = client.post("/m/test-token/auto-cluster")
    assert r.status_code == 200
    body = r.json()
    assert body["themes_created"] >= 1

    # Reveal view loads
    r = client.get("/m/test-token/reveal")
    assert r.status_code == 200

    # End event
    r = client.post("/m/test-token/end-event")
    assert r.status_code == 200

    # Wait for background package generation to complete
    import time
    from idea_jam import repo
    for _ in range(50):
        time.sleep(0.1)
        s = repo.get_event_state()
        if s["packages_status"] == "complete":
            break
    else:
        pytest.fail("packages did not complete within 5 seconds")

    # Package retrieval as attendee 2 (current cookies)
    r = client.get("/package")
    assert r.status_code == 200
    assert "watch my deploys and alert me" in r.text
