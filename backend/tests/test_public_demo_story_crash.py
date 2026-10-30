"""Reproduce the public-demo e2e abort: stepping the story to 04:21 kills the server.

Walks every care checkpoint through the same endpoints the frontend hits
per step (POST investigations, then GET events/visual/sources/context/
investigation/watcher/trace) using the real recordings in backend/eval.
"""
from aria_home.public_demo import CHECKPOINTS

SCENARIO = "care_home_v1"
CHECKPOINT_LIST = list(CHECKPOINTS[SCENARIO])


def _public_client(tmp_path, monkeypatch):
    from aria_home.app import create_app

    for var in ("ARIA_HOME_MODEL_ENABLED", "ARIA_HOME_WHATSAPP_LIVE", "ARIA_HOME_EMPORIA_LIVE",
                "ARIA_HOME_VISUAL_LIVE", "ARIA_HOME_NEST_LIVE", "ARIA_HOME_E2E_HOOKS", "MODEL_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(tmp_path / "sessions"))
    return create_app().test_client()


def test_story_steps_survive_every_checkpoint(tmp_path, monkeypatch):
    client = _public_client(tmp_path, monkeypatch)
    assert CHECKPOINT_LIST, "expected care checkpoints"
    for at in CHECKPOINT_LIST:
        query = {"scenario": SCENARIO, "at": at}
        posted = client.post("/api/investigations", query_string=query)
        assert posted.status_code < 500, (at, posted.status_code, posted.get_data(as_text=True)[:500])
        for endpoint in ("/api/events", "/api/visual", "/api/sources", "/api/context",
                         "/api/investigation", "/api/watcher", "/api/trace"):
            response = client.get(endpoint, query_string=query)
            assert response.status_code < 500, (at, endpoint, response.status_code,
                                               response.get_data(as_text=True)[:500])
        image = client.get("/api/visual/image", query_string=query)
        assert image.status_code < 500, (at, image.status_code)
