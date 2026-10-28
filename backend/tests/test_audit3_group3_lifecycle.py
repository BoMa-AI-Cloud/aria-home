import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aria_home.app as app_module
from aria_home.app import create_app
from aria_home.investigator import inference_identity
from aria_home.provider import MockProvider, ProviderResult
from aria_home.scenario import load_scenario
from aria_home.store import Store

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
AT = "2026-01-16T18:00:00-05:00"
URL = f"/api/investigations?scenario=demo_v1&at={AT}"
GET_URL = f"/api/investigation?scenario=demo_v1&at={AT}"


class CountingProvider:
    mode = "mock"
    model_id = "muse-spark-1.3"

    def __init__(self, fail=False, delay=0.0):
        self.calls = 0
        self.fail = fail
        self.delay = delay
        self._lock = threading.Lock()
        self._inner = MockProvider()

    def generate(self, prompt=None, *, messages=None, max_tokens=None):
        with self._lock:
            self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.fail:
            return ProviderResult(ok=False, mode="mock", requested_model=self.model_id, answered_model=self.model_id, text=None, latency_ms=1.0, error="server_error")
        return self._inner.generate(prompt, messages=messages, max_tokens=max_tokens)


def _app(tmp_path, monkeypatch, provider, name="api.db"):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / name))
    monkeypatch.setattr(app_module, "get_provider", lambda *a, **k: provider)
    return create_app()


def _identity(provider):
    scenario = load_scenario(SCENARIOS / "demo_v1")
    at = datetime.fromisoformat(AT)
    return inference_identity(scenario, at, provider=provider)


def _expire(db_path, identity_key):
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE inference_requests SET lease_expires_at = ? WHERE identity_key = ?", ("2000-01-01T00:00:00+00:00", identity_key))
    conn.commit()
    conn.close()


def test_restart_with_abandoned_claim_requires_explicit_recovery(tmp_path, monkeypatch):
    provider = CountingProvider()
    db = tmp_path / "api.db"
    identity = _identity(provider)
    claimed, claim = Store(db).claim_inference(identity)
    assert claimed and claim["owner_id"] and claim["lease_expires_at"]
    _expire(db, identity["identity_key"])

    client = _app(tmp_path, monkeypatch, provider).test_client()
    ordinary = client.post(URL)
    assert ordinary.status_code == 409, ordinary.get_json()
    assert ordinary.get_json()["status"] == "recovery_required"
    assert provider.calls == 0
    got = client.get(GET_URL)
    assert got.status_code == 409, got.get_json()
    assert got.get_json()["status"] == "recovery_required"
    assert provider.calls == 0
    assert Store(db).get_inference(identity["identity_key"])["state"] == "recovery_required"

    recovered = client.post(URL + "&retry=true")
    assert recovered.status_code == 200, recovered.get_json()
    assert provider.calls == 1
    again = client.post(URL)
    assert again.status_code == 200
    assert provider.calls == 1


def test_active_claim_not_stolen_by_ordinary_or_retry(tmp_path, monkeypatch):
    provider = CountingProvider()
    db = tmp_path / "api.db"
    identity = _identity(provider)
    claimed, _ = Store(db).claim_inference(identity)
    assert claimed
    client = _app(tmp_path, monkeypatch, provider).test_client()
    for suffix in ("", "&retry=true"):
        resp = client.post(URL + suffix)
        assert resp.status_code == 202, resp.get_json()
        assert resp.get_json()["status"] == "pending"
    got = client.get(GET_URL)
    assert got.status_code == 202
    assert provider.calls == 0


def test_concurrent_recovery_has_single_owner_and_call(tmp_path, monkeypatch):
    provider = CountingProvider(delay=0.5)
    db = tmp_path / "api.db"
    identity = _identity(provider)
    assert Store(db).claim_inference(identity)[0]
    _expire(db, identity["identity_key"])
    app = _app(tmp_path, monkeypatch, provider)
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: app.test_client().post(URL + "&retry=true"), range(8)))
    codes = sorted(r.status_code for r in responses)
    assert provider.calls == 1, codes
    assert codes == [200] + [202] * 7, codes
    assert Store(db).get_inference(identity["identity_key"])["state"] == "completed"


def test_late_completion_by_old_owner_does_not_overwrite(tmp_path):
    store = Store(tmp_path / "late.db")
    identity = _identity(CountingProvider())
    claimed, first = store.claim_inference(identity)
    assert claimed
    _expire(tmp_path / "late.db", identity["identity_key"])
    claimed, second = store.claim_inference(identity, retry=True)
    assert claimed and second["owner_id"] != first["owner_id"]
    newer = {"status": "ok", "output": {"version": "newer"}, "model_id": "m", "provider_mode": "mock"}
    older = {"status": "ok", "output": {"version": "older"}, "model_id": "m", "provider_mode": "mock"}
    accepted = store.complete_inference(identity["identity_key"], newer, "completed", owner_id=second["owner_id"])
    assert accepted["completion_accepted"] is True
    late = store.complete_inference(identity["identity_key"], older, "completed", owner_id=first["owner_id"])
    assert late["completion_accepted"] is False
    row = store.get_inference(identity["identity_key"])
    assert row["accepted_result"]["output"] == {"version": "newer"}
    assert store.get_investigation(identity["investigation_id"])["output"] == {"version": "newer"}


def test_get_never_runs_inference_and_returns_stored_after_post(tmp_path, monkeypatch):
    provider = CountingProvider()
    client = _app(tmp_path, monkeypatch, provider).test_client()
    first = client.get(GET_URL)
    second = client.get(GET_URL)
    assert first.status_code == second.status_code == 200
    assert first.get_json()["status"] == "unavailable"
    assert first.get_json()["inference_state"] == "not_started"
    assert first.get_json()["readiness"] == second.get_json()["readiness"]
    assert provider.calls == 0

    created = client.post(URL)
    assert created.status_code == 200, created.get_json()
    assert provider.calls == 1
    stored = client.get(GET_URL)
    assert stored.status_code == 200
    assert stored.get_json()["status"] == "ok"
    assert stored.get_json()["output"] == created.get_json()["investigation"]["output"]
    assert provider.calls == 1
    repeated = client.post(URL)
    assert repeated.status_code == 200
    assert provider.calls == 1


def _manager_notification(client):
    resp = client.post("/api/investigations?scenario=demo_video_v1&at=2026-01-16T16:31:00-05:00")
    assert resp.status_code == 200, resp.get_json()
    inv_id = resp.get_json()["investigation_id"]
    rows = client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"]
    manager = next(r for r in rows if r["audience"] == "property_manager")
    assert manager["state"] == "simulated_delivered"
    return inv_id, manager


def test_ack_validation_reproductions_and_idempotency(tmp_path, monkeypatch):
    provider = CountingProvider()
    client = _app(tmp_path, monkeypatch, provider, name="ack.db").test_client()
    _, manager = _manager_notification(client)
    url = f"/api/notifications/{manager['id']}/ack"

    early = client.post(url, json={"actor": "property_manager", "at": "2000-01-01T00:00:00Z"})
    assert early.status_code == 400, early.get_json()
    numeric = client.post(url, json={"actor": "property_manager", "at": 123})
    assert numeric.status_code == 400, numeric.get_json()
    bad_body = client.post(url, json=["bad"])
    assert bad_body.status_code == 400, bad_body.get_json()
    intruder = client.post(url, json={"actor": "intruder", "at": "2026-01-16T16:37:00-05:00"})
    assert intruder.status_code == 403, intruder.get_json()
    naive = client.post(url, json={"actor": "property_manager", "at": "2026-01-16T16:37:00"})
    assert naive.status_code == 400, naive.get_json()
    numeric_actor = client.post(url, json={"actor": 123, "at": "2026-01-16T16:37:00-05:00"})
    assert numeric_actor.status_code == 400, numeric_actor.get_json()
    wrong_audience = client.post(url, json={"actor": "homeowner", "at": "2026-01-16T16:37:00-05:00"})
    assert wrong_audience.status_code == 403, wrong_audience.get_json()

    valid = client.post(url, json={"actor": "property_manager", "at": "2026-01-16T16:37:00-05:00"})
    assert valid.status_code == 200, valid.get_json()
    assert valid.get_json()["message"] == "acknowledged, not resolved"
    assert len(valid.get_json()["acks"]) == 1
    repeated = client.post(url, json={"actor": "property_manager", "at": "2026-01-16T16:37:00-05:00"})
    assert repeated.status_code == 200
    assert len(repeated.get_json()["acks"]) == 1
    at_replay_ack = client.get(f"/api/notifications?investigation_id={manager['investigation_id']}&at=2026-01-16T16:37:00-05:00").get_json()["notifications"]
    shown = next(r for r in at_replay_ack if r["id"] == manager["id"])
    assert len(shown["acks"]) == 1
    before_ack = client.get(f"/api/notifications?investigation_id={manager['investigation_id']}&at=2026-01-16T16:36:00-05:00").get_json()["notifications"]
    hidden = next(r for r in before_ack if r["id"] == manager["id"])
    assert hidden["acks"] == []


def test_ack_refused_and_queued_notices_rejected(tmp_path, monkeypatch):
    provider = CountingProvider()
    client = _app(tmp_path, monkeypatch, provider, name="ack2.db").test_client()
    inv_id, _ = _manager_notification(client)
    store = Store(tmp_path / "ack2.db")
    for state in ("refused", "queued"):
        row = store.save_notification(investigation_id=inv_id, audience="property_manager", kind="manager_alert", idempotency_key=f"ack-state-{state}", payload={"audience": "property_manager", "kind": "manager_alert"}, created_at="2026-01-16T16:31:00-05:00", state=state, refusal_reason="manager_not_authorized" if state == "refused" else None)
        resp = client.post(f"/api/notifications/{row['id']}/ack", json={"actor": "property_manager", "at": "2026-01-16T16:37:00-05:00"})
        assert resp.status_code == 409, (state, resp.get_json())
        assert store.list_acks(row["id"]) == []
