"""Follow-ups replay fields: per-step metrics and the per-step recorded answer.

The House lead and the Reasoning tab must be governed by the replay time, not
by the creation-time investigation. Every follow-ups response therefore carries
`metrics` (exactly the indoor trend and target gap `GET /api/metrics` reports
for the same scenario and time) and `recorded_investigation` (the recorded
muse-spark-1.3 answer matching that replay time, with its bound review, or the
labelled fallback when no recording matches).
"""
import pytest

from aria_home.app import create_app
from aria_home.recorded import NO_RECORDED_LABEL

T1920 = "2026-01-16T19:20:00-05:00"
CHECKPOINTS = [
    "2026-01-17T02:31:00-05:00",
    "2026-01-17T02:45:00-05:00",
    "2026-01-17T04:21:00-05:00",
    "2026-01-17T04:51:00-05:00",
    "2026-01-17T06:21:00-05:00",
    "2026-01-17T06:45:00-05:00",
    "2026-01-17T07:01:00-05:00",
]

SCRUB_VARS = [
    "ARIA_HOME_PROVIDER_URL",
    "ARIA_HOME_MODEL_ID",
    "MODEL_API_KEY",
    "ARIA_HOME_MODEL_ENABLED",
    "ARIA_HOME_WHATSAPP_LIVE",
    "WHATSAPP_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "WHATSAPP_TEST_RECIPIENT",
    "ARIA_HOME_EMPORIA_LIVE",
    "EMPORIA_EMAIL",
    "EMPORIA_PASSWORD",
    "ARIA_HOME_VISUAL_LIVE",
    "ARIA_HOME_E2E_HOOKS",
    "ARIA_HOME_DB_PATH",
    "ARIA_HOME_BASETEN_ENABLED",
    "BASETEN_API_KEY",
    "ARIA_HOME_INVESTIGATION_MAX_TOKENS",
    "ARIA_HOME_PUBLIC_DEMO_MAX_BYTES",
    "ARIA_HOME_RECORDED_DIR",
]


@pytest.fixture
def story_env(monkeypatch, tmp_path):
    for var in SCRUB_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(tmp_path / "sessions"))
    return tmp_path


@pytest.fixture
def story_env_no_recordings(monkeypatch, tmp_path):
    for var in SCRUB_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(tmp_path / "sessions"))
    recorded = tmp_path / "recorded"
    recorded.mkdir()
    monkeypatch.setenv("ARIA_HOME_RECORDED_DIR", str(recorded))
    return tmp_path


def _start(client):
    resp = client.post(f"/api/investigations?scenario=care_home_v1&at={T1920}")
    assert resp.status_code == 200
    return resp.get_json()["investigation_id"]


def _follow_ups(client, inv_id, at):
    resp = client.get(f"/api/follow-ups/{inv_id}?at={at}")
    assert resp.status_code == 200
    return resp.get_json()


def test_followups_metrics_match_metrics_endpoint_at_every_checkpoint(story_env):
    client = create_app().test_client()
    inv_id = _start(client)
    for at in CHECKPOINTS:
        body = _follow_ups(client, inv_id, at)
        metrics = client.get("/api/metrics", query_string={"scenario": "care_home_v1", "at": at}).get_json()
        assert body["metrics"] == {"indoor_trend": metrics["indoor_trend"], "target_gap": metrics["target_gap"]}


def test_followups_metrics_rates_follow_the_replay_time(story_env):
    client = create_app().test_client()
    inv_id = _start(client)
    assert _follow_ups(client, inv_id, CHECKPOINTS[0])["metrics"]["indoor_trend"]["rate_per_hour"] == pytest.approx(-0.2, abs=0.05)
    assert _follow_ups(client, inv_id, CHECKPOINTS[4])["metrics"]["indoor_trend"]["rate_per_hour"] == pytest.approx(5.5, abs=0.05)


def test_followups_recorded_investigation_matches_replay_time(story_env):
    client = create_app().test_client()
    inv_id = _start(client)
    early = _follow_ups(client, inv_id, CHECKPOINTS[0])["recorded_investigation"]
    assert early["provider_mode"] == "recorded"
    assert early["evaluated_at"] == CHECKPOINTS[0]
    assert early["recorded_provenance"]["model_id"] == "muse-spark-1.3"
    assert early["output"]["interpretation"]
    assert early["recorded_review"]["answer_bound"] is True
    assert early["recorded_review"]["review"]["verdict"] == "no_issues"
    late = _follow_ups(client, inv_id, CHECKPOINTS[4])["recorded_investigation"]
    assert late["provider_mode"] == "recorded"
    assert late["evaluated_at"] == CHECKPOINTS[4]
    assert late["recorded_review"]["answer_bound"] is True
    assert late["output"]["interpretation"] != early["output"]["interpretation"]


def test_followups_recorded_investigation_fallback_is_labelled(story_env_no_recordings):
    client = create_app().test_client()
    inv_id = _start(client)
    recorded = _follow_ups(client, inv_id, CHECKPOINTS[0])["recorded_investigation"]
    assert recorded["status"] == "unavailable"
    assert NO_RECORDED_LABEL in recorded["reasons"]
    assert recorded["evaluated_at"] == CHECKPOINTS[0]
