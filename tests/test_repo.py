import importlib
import pytest


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    import idea_jam.db as db
    importlib.reload(db)
    import idea_jam.repo as repo
    importlib.reload(repo)
    db.init_db()
    return repo


def test_create_and_get_participant(repo):
    p = repo.create_participant()
    fetched = repo.get_participant(p["id"])
    assert fetched["id"] == p["id"]
    assert fetched["display_name"] == p["display_name"]


def test_rename_and_regenerate(repo):
    p = repo.create_participant()
    repo.rename_participant(p["id"], "custom-name")
    assert repo.get_participant(p["id"])["display_name"] == "custom-name"
    new_name = repo.regenerate_participant_name(p["id"])
    assert new_name != "custom-name"


def test_add_and_list_ideas(repo):
    p = repo.create_participant()
    a = repo.add_idea(p["id"], "first idea")
    b = repo.add_idea(p["id"], "second idea")
    own = repo.list_ideas_for_participant(p["id"])
    assert {i["text"] for i in own} == {"first idea", "second idea"}
    assert own[0]["id"] in {a["id"], b["id"]}


def test_create_theme_assigns_position(repo):
    t1 = repo.create_theme("alpha")
    t2 = repo.create_theme("beta")
    assert t2["position"] == t1["position"] + 1
    assert [t["name"] for t in repo.list_themes()] == ["alpha", "beta"]


def test_move_idea_to_theme_and_back(repo):
    p = repo.create_participant()
    i = repo.add_idea(p["id"], "x")
    t = repo.create_theme("alpha")
    repo.move_idea(i["id"], t["id"], 0)
    fetched = repo.list_all_ideas()[0]
    assert fetched["theme_id"] == t["id"]
    repo.move_idea(i["id"], None, None)
    fetched = repo.list_all_ideas()[0]
    assert fetched["theme_id"] is None


def test_delete_theme_unsets_ideas(repo):
    p = repo.create_participant()
    i = repo.add_idea(p["id"], "x")
    t = repo.create_theme("alpha")
    repo.move_idea(i["id"], t["id"], 0)
    repo.delete_theme(t["id"])
    fetched = repo.list_all_ideas()[0]
    assert fetched["theme_id"] is None
    assert repo.list_themes() == []


def test_toggle_star(repo):
    p = repo.create_participant()
    i = repo.add_idea(p["id"], "x")
    assert repo.toggle_star(i["id"]) is True
    assert repo.toggle_star(i["id"]) is False


def test_event_state_singleton_and_end(repo):
    s = repo.get_event_state()
    assert s["ended"] is False
    assert s["packages_status"] == "not_started"
    repo.end_event()
    repo.set_packages_status("generating")
    s2 = repo.get_event_state()
    assert s2["ended"] is True
    assert s2["packages_status"] == "generating"


def test_delete_idea(repo):
    p = repo.create_participant()
    i = repo.add_idea(p["id"], "to delete")
    repo.delete_idea(i["id"])
    assert repo.get_idea(i["id"]) is None


def test_update_idea_text(repo):
    p = repo.create_participant()
    i = repo.add_idea(p["id"], "original")
    repo.update_idea_text(i["id"], "revised")
    fetched = repo.get_idea(i["id"])
    assert fetched["text"] == "revised"
