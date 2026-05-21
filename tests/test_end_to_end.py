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
    # Attendee 1 takes a random name and gets a cookie
    r = client.post("/me/random-name", follow_redirects=False)
    assert r.status_code == 303
    a1_cookie = client.cookies.get("ij_pid")
    assert a1_cookie

    # Attendee 1 submits two ideas
    r = client.post("/ideas", data={"text": "automate my email triage"})
    assert r.status_code == 200
    r = client.post("/ideas", data={"text": "summarise my standup notes"})
    assert r.status_code == 200

    # Attendee 2 (fresh client cookies)
    client.cookies.clear()
    r = client.post("/me/random-name", follow_redirects=False)
    assert r.status_code == 303
    r = client.post("/ideas", data={"text": "watch my deploys and alert me"})
    assert r.status_code == 200

    # Moderator dashboard requires login - 404 without cookie
    r = client.get("/m/dashboard")
    assert r.status_code == 404

    # Wrong token re-renders the login page (200 + error)
    r = client.post("/m/login", data={"token": "wrong-token"}, follow_redirects=False)
    assert r.status_code == 200
    assert "invalid" in r.text.lower() or "moderator" in r.text.lower()

    # Log in with the right token (sets ij_mod cookie)
    r = client.post("/m/login", data={"token": "test-token"}, follow_redirects=False)
    assert r.status_code == 303

    # Moderator dashboard reachable with cookie
    r = client.get("/m/dashboard")
    assert r.status_code == 200
    assert "automate my email triage" in r.text

    # Auto-cluster
    r = client.post("/m/auto-cluster")
    assert r.status_code == 200
    body = r.json()
    assert body["themes_created"] >= 1

    # Reveal view loads
    r = client.get("/m/reveal")
    assert r.status_code == 200

    # End event
    r = client.post("/m/end-event")
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


def test_first_visit_shows_name_entry(client):
    client.cookies.clear()
    r = client.get("/")
    assert r.status_code == 200
    assert "welcome to the jam" in r.text.lower() or "pick a name" in r.text.lower()
    # Should NOT have created a participant yet
    assert client.cookies.get("ij_pid") is None


def test_claim_name_creates_participant(client):
    client.cookies.clear()
    r = client.post("/me/claim-name", data={"display_name": "alice"}, follow_redirects=False)
    assert r.status_code == 303
    pid = client.cookies.get("ij_pid")
    assert pid
    # Verify the home page now shows
    r = client.get("/")
    assert r.status_code == 200
    assert "alice" in r.text


def test_random_name_creates_participant(client):
    client.cookies.clear()
    r = client.post("/me/random-name", follow_redirects=False)
    assert r.status_code == 303
    assert client.cookies.get("ij_pid")


def test_delete_own_idea(client):
    client.cookies.clear()
    client.post("/me/claim-name", data={"display_name": "deleter"}, follow_redirects=False)
    r = client.post("/ideas", data={"text": "idea to delete"})
    assert r.status_code == 200
    # Get the idea id from the database
    from idea_jam import repo
    pid = client.cookies.get("ij_pid")
    ideas = repo.list_ideas_for_participant(pid)
    assert len(ideas) == 1
    iid = ideas[0]["id"]
    r = client.delete(f"/ideas/{iid}")
    assert r.status_code == 200
    assert repo.list_ideas_for_participant(pid) == []


def test_edit_own_idea(client):
    client.cookies.clear()
    client.post("/me/claim-name", data={"display_name": "editor"}, follow_redirects=False)
    client.post("/ideas", data={"text": "original text"})
    from idea_jam import repo
    pid = client.cookies.get("ij_pid")
    iid = repo.list_ideas_for_participant(pid)[0]["id"]
    r = client.post(f"/ideas/{iid}/edit", data={"text": "revised text"})
    assert r.status_code == 200
    updated = repo.get_idea(iid)
    assert updated["text"] == "revised text"


def test_cannot_delete_others_ideas(client):
    client.cookies.clear()
    # Attendee 1 creates an idea
    client.post("/me/claim-name", data={"display_name": "alice"}, follow_redirects=False)
    client.post("/ideas", data={"text": "alice's idea"})
    from idea_jam import repo
    a1_pid = client.cookies.get("ij_pid")
    iid = repo.list_ideas_for_participant(a1_pid)[0]["id"]
    # Attendee 2 tries to delete it
    client.cookies.clear()
    client.post("/me/claim-name", data={"display_name": "mallory"}, follow_redirects=False)
    r = client.delete(f"/ideas/{iid}")
    assert r.status_code == 404
    # Confirm the idea still exists
    assert repo.get_idea(iid) is not None
