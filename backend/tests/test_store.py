import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aria_home.app import create_app
from aria_home.investigator import investigate
from aria_home.outcomes import evaluate_outcome, follow_up_for
from aria_home.provider import get_provider
from aria_home.scenario import load_scenario
from aria_home.store import Store

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
TZ = timezone(timedelta(hours=-5))
AT = datetime(2026, 1, 16, 18, 0, tzinfo=TZ)


def _saved(store, scenario_name="demo_v1"):
    scenario = load_scenario(SCENARIOS / scenario_name)
    result = investigate(scenario, AT, get_provider())
    inv_id = store.save_investigation(result, investigation_id="inv-test-1", scenario=scenario.manifest.id, evaluated_at=AT)
    follow_up = follow_up_for(scenario, inv_id, AT)
    store.save_follow_up(follow_up)
    return scenario, result, follow_up


def test_restart_keeps_investigation_and_follow_up(tmp_path):
    db = tmp_path / "aria.db"
    store = Store(db)
    scenario, result, follow_up = _saved(store)
    store.close()

    reopened = Store(db)
    saved = reopened.get_investigation("inv-test-1")
    assert saved is not None
    assert saved["scenario"] == "demo_v1"
    assert saved["status"] == result.status
    assert saved["output"] == result.output.model_dump(mode="json")
    assert saved["model_id"] == result.model_id
    assert saved["provider_mode"] == result.provider_mode
    assert reopened.get_follow_up("inv-test-1") == follow_up
    reopened.close()


def test_saving_twice_and_reevaluating_same_now_are_idempotent(tmp_path):
    db = tmp_path / "aria.db"
    store = Store(db)
    scenario, _, follow_up = _saved(store)
    _saved(store)

    now = datetime(2026, 1, 16, 20, 30, tzinfo=TZ)
    outcome = evaluate_outcome(follow_up, scenario.records, now)
    store.record_outcome("inv-test-1", outcome)
    first = store.get_follow_up_row("inv-test-1")
    store.record_outcome("inv-test-1", outcome)
    store.save_follow_up(follow_up, outcome=outcome)
    assert store.get_follow_up_row("inv-test-1") == first
    assert first["last_status"] == outcome.status.value
    assert first["last_evaluated_at"] == now.isoformat()
    assert first["supporting_ids"] == outcome.supporting_ids

    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM investigations").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM follow_ups").fetchone()[0] == 1
    conn.close()
    store.close()


def test_store_path_from_env(tmp_path, monkeypatch):
    db = tmp_path / "from-env.db"
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(db))
    store = Store()
    assert store.path == db
    _saved(store)
    store.close()
    assert db.is_file()


def test_outcome_history_grows_idempotent_and_survives_restart(tmp_path, monkeypatch):
    db = tmp_path / "history.db"
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(db))
    client = create_app().test_client()

    resp = client.post("/api/investigations?scenario=demo_recovery_v1&at=2026-01-16T18:00:00-05:00")
    assert resp.status_code == 200
    inv_id = resp.get_json()["investigation_id"]

    resp = client.get(f"/api/follow-ups/{inv_id}?at=2026-01-16T19:00:00-05:00")
    assert resp.status_code == 200
    assert [e["status"] for e in resp.get_json()["history"]] == ["warming_observed"]

    resp = client.get(f"/api/follow-ups/{inv_id}?at=2026-01-16T20:31:00-05:00")
    assert resp.status_code == 200
    assert [e["status"] for e in resp.get_json()["history"]] == ["warming_observed", "target_reached"]

    resp = client.get(f"/api/follow-ups/{inv_id}?at=2026-01-16T20:31:00-05:00")
    assert resp.status_code == 200
    assert [e["status"] for e in resp.get_json()["history"]] == ["warming_observed", "target_reached"]

    reopened = Store(db)
    assert [e["status"] for e in reopened.list_outcomes(inv_id)] == ["warming_observed", "target_reached"]
    reopened.close()


def test_post_then_get_follow_up(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    client = create_app().test_client()

    resp = client.post("/api/investigations?scenario=demo_recovery_v1&at=2026-01-16T18:00:00-05:00")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["data_mode"] == "synthetic"
    assert payload["investigation"]["id"] == payload["investigation_id"]
    assert payload["follow_up"]["investigation_id"] == payload["investigation_id"]

    inv_id = payload["investigation_id"]
    resp = client.get(f"/api/follow-ups/{inv_id}?at=2026-01-16T20:30:20-05:00")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["data_mode"] == "synthetic"
    assert payload["status"] == "target_reached"
    assert payload["outcome"]["status"] == "target_reached"
    assert payload["follow_up"]["last_status"] == "target_reached"
