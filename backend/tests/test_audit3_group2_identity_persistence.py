import copy
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import aria_home.app as app_module
from aria_home.app import create_app
from aria_home.investigator import build_evidence_pack, inference_identity
from aria_home.provider import MockProvider, ProviderResult
from aria_home.scenario import load_scenario
from aria_home.store import Store

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
AT = "2026-01-16T18:00:00-05:00"
URL = f"/api/investigations?scenario=demo_v1&at={AT}"


class FakeProvider:
    def __init__(self, mode="mock", model_id="muse-spark-1.3", provider_url=None, api_key=None, fail=False, delay=0.0):
        self.mode = mode
        self.model_id = model_id
        self.provider_url = provider_url
        self.api_key = api_key
        self.max_tokens = 256
        self.fail = fail
        self.delay = delay
        self.calls = 0
        self._lock = threading.Lock()
        self._inner = MockProvider()

    def generate(self, prompt=None, *, messages=None, max_tokens=None):
        with self._lock:
            self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.fail:
            return ProviderResult(ok=False, mode=self.mode, requested_model="muse-spark-1.3", answered_model="muse-spark-1.3", text=None, latency_ms=1.0, error="server_error")
        return self._inner.generate(prompt, messages=messages, max_tokens=max_tokens)


def _client(tmp_path, monkeypatch, provider, name="api.db"):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / name))
    current = {"provider": provider}
    monkeypatch.setattr(app_module, "get_provider", lambda *a, **k: current["provider"])
    return create_app().test_client(), current


def _scenario_with_indoor(value, at_text="2026-01-16T17:56:00-05:00"):
    scenario = load_scenario(SCENARIOS / "demo_v1")
    mutated = copy.deepcopy(scenario)
    for record in mutated.records:
        if record.quantity == "indoor_temp":
            record.value = value
    return mutated, datetime.fromisoformat(at_text)


def test_rounding_reproduction_through_post(tmp_path, monkeypatch):
    scenario, at = _scenario_with_indoor(68.04)
    provider = FakeProvider()
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "round.db"))
    monkeypatch.setattr(app_module, "get_provider", lambda *a, **k: provider)
    monkeypatch.setattr(app_module, "load_scenario", lambda path: scenario)
    client = create_app().test_client()
    url = "/api/investigations?scenario=demo_v1&at=2026-01-16T17:56:00-05:00"
    first = client.post(url)
    assert first.status_code == 200, first.get_json()
    assert first.get_json()["computed_readiness"] == "on_track"
    assert first.get_json()["deduplicated"] is False
    for record in scenario.records:
        if record.quantity == "indoor_temp":
            record.value = 67.96
    second = client.post(url)
    assert second.status_code == 200, second.get_json()
    assert second.get_json()["deduplicated"] is False
    assert second.get_json()["investigation_id"] != first.get_json()["investigation_id"]
    assert second.get_json()["input_revision"] != first.get_json()["input_revision"]
    assert second.get_json()["computed_readiness"] == "at_risk"
    assert provider.calls == 2
    third = client.post(url)
    assert third.get_json()["deduplicated"] is True
    assert third.get_json()["computed_readiness"] == "at_risk"
    assert provider.calls == 2


def test_input_revision_full_precision_stability_and_presentation():
    scenario, at = _scenario_with_indoor(68.04)
    base = inference_identity(scenario, at, provider=FakeProvider())
    changed, _ = _scenario_with_indoor(67.96)
    assert inference_identity(changed, at, provider=FakeProvider())["input_revision"] != base["input_revision"]
    reordered = copy.deepcopy(scenario)
    reordered.records = list(reversed(reordered.records))
    assert inference_identity(reordered, at, provider=FakeProvider())["input_revision"] == base["input_revision"]
    assert inference_identity(scenario, at.astimezone(timezone.utc), provider=FakeProvider())["identity_key"] == base["identity_key"]
    shifted = copy.deepcopy(scenario)
    for record in shifted.records:
        if record.quantity == "indoor_temp":
            record.observed_at = record.observed_at.astimezone(timezone.utc)
            record.received_at = record.received_at.astimezone(timezone.utc)
    assert inference_identity(shifted, at, provider=FakeProvider())["input_revision"] == base["input_revision"]
    pack = build_evidence_pack(scenario, at)
    presentation = copy.deepcopy(pack)
    presentation["metrics"]["indoor_trend"]["last_value"] = 999.0
    presentation["trip"]["title"] = {"untrusted_text": "changed presentation", "quoted": '"changed"'}
    assert inference_identity(scenario, at, pack=presentation, provider=FakeProvider())["input_revision"] == base["input_revision"]


def test_provider_identity_changes_and_key_rotation(tmp_path, monkeypatch):
    mock = FakeProvider(mode="mock", api_key="SECRET-KEY-ONE")
    client, current = _client(tmp_path, monkeypatch, mock)
    first = client.post(URL)
    assert first.status_code == 200 and mock.calls == 1
    assert "SECRET-KEY-ONE" not in first.get_data(as_text=True)

    live = FakeProvider(mode="live", provider_url="https://provider-a.example/v1/messages?api_key=SECRET-KEY-ONE", api_key="SECRET-KEY-ONE")
    current["provider"] = live
    second = client.post(URL)
    assert second.status_code == 200 and live.calls == 1
    assert second.get_json()["investigation_id"] != first.get_json()["investigation_id"]
    assert second.get_json()["deduplicated"] is False

    other_model = FakeProvider(mode="live", model_id="muse-wonder-1.0", provider_url="https://provider-a.example/v1/messages", api_key="SECRET-KEY-ONE")
    current["provider"] = other_model
    third = client.post(URL)
    assert other_model.calls == 1 and third.get_json()["investigation_id"] != second.get_json()["investigation_id"]

    other_endpoint = FakeProvider(mode="live", model_id="muse-wonder-1.0", provider_url="https://provider-b.example/v1/messages", api_key="SECRET-KEY-ONE")
    current["provider"] = other_endpoint
    fourth = client.post(URL)
    assert other_endpoint.calls == 1 and fourth.get_json()["investigation_id"] != third.get_json()["investigation_id"]

    rotated = FakeProvider(mode="live", model_id="muse-wonder-1.0", provider_url="https://provider-b.example/v1/messages?x=1", api_key="SECRET-KEY-TWO")
    current["provider"] = rotated
    fifth = client.post(URL)
    assert rotated.calls == 0
    assert fifth.get_json()["deduplicated"] is True
    assert fifth.get_json()["investigation_id"] == fourth.get_json()["investigation_id"]
    assert "SECRET-KEY" not in fifth.get_data(as_text=True)
    db_bytes = (tmp_path / "api.db").read_bytes()
    assert b"SECRET-KEY-ONE" not in db_bytes and b"SECRET-KEY-TWO" not in db_bytes


def test_failed_retry_persists_accepted_result_and_history(tmp_path, monkeypatch):
    provider = FakeProvider(fail=True)
    client, _ = _client(tmp_path, monkeypatch, provider)
    first = client.post(URL)
    inv_id = first.get_json()["investigation_id"]
    assert first.get_json()["investigation"]["status"] == "unavailable"
    store = Store(tmp_path / "api.db")
    assert store.get_investigation(inv_id)["status"] == "unavailable"
    assert store.get_investigation(inv_id)["output"] is None
    first_notifications = first.get_json()["notifications"]

    provider.fail = False
    retried = client.post(URL + "&retry=true")
    assert retried.status_code == 200, retried.get_json()
    assert retried.get_json()["investigation"]["status"] == "ok"
    assert retried.get_json()["attempts"] == 2
    saved = store.get_investigation(inv_id)
    assert saved["status"] == "ok"
    assert saved["output"] is not None
    assert saved["output"] == retried.get_json()["investigation"]["output"]
    inference = store.get_inference(retried.get_json()["identity_key"])
    assert inference["accepted_result"]["status"] == "ok"
    assert [a["state"] for a in inference["attempt_history"]] == ["failed", "completed"]
    assert [a["status"] for a in inference["attempt_history"]] == ["unavailable", "ok"]

    again = client.post(URL + "&retry=true")
    assert provider.calls == 2
    assert again.get_json()["deduplicated"] is True
    assert store.get_inference(retried.get_json()["identity_key"])["attempt_history"] == inference["attempt_history"]

    follow = client.get(f"/api/follow-ups/{inv_id}?at=2026-01-16T19:00:00-05:00")
    assert follow.status_code == 200, follow.get_json()
    assert follow.get_json()["follow_up"]["investigation_id"] == inv_id
    notifications = client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"]
    assert [n["id"] for n in notifications] == [n["id"] for n in first_notifications]
    assert retried.get_json()["notifications"] == first_notifications


def test_accepted_result_not_downgraded_by_later_failed_save(tmp_path):
    store = Store(tmp_path / "accepted.db")
    identity_scenario = load_scenario(SCENARIOS / "demo_v1")
    at = datetime.fromisoformat(AT)
    ok = {"status": "ok", "output": {"verified_facts": ["x"]}, "model_id": "m", "provider_mode": "mock"}
    failed = {"status": "unavailable", "output": None, "model_id": "m", "provider_mode": "mock"}
    store.save_investigation(ok, investigation_id="inv-x", scenario=identity_scenario.manifest.id, evaluated_at=at)
    store.save_investigation(failed, investigation_id="inv-x", scenario=identity_scenario.manifest.id, evaluated_at=at)
    assert store.get_investigation("inv-x")["status"] == "ok"
    assert store.get_investigation("inv-x")["output"] == {"verified_facts": ["x"]}


def test_failure_during_persistence_rolls_back_and_can_complete(tmp_path):
    store = Store(tmp_path / "persist.db")
    scenario = load_scenario(SCENARIOS / "demo_v1")
    at = datetime.fromisoformat(AT)
    identity = inference_identity(scenario, at, provider=FakeProvider())
    claimed, _ = store.claim_inference(identity)
    assert claimed
    conn = sqlite3.connect(tmp_path / "persist.db")
    conn.execute("CREATE TRIGGER fail_inv BEFORE INSERT ON investigations BEGIN SELECT RAISE(ABORT, 'boom'); END")
    conn.commit(); conn.close()
    with pytest.raises(sqlite3.Error):
        store.complete_inference(identity["identity_key"], {"status": "ok", "output": {"a": 1}}, "completed")
    row = store.get_inference(identity["identity_key"])
    assert row["state"] == "pending" and row["accepted_result"] is None
    assert row["attempt_history"][0]["state"] == "pending"
    assert store.get_investigation(identity["investigation_id"]) is None
    conn = sqlite3.connect(tmp_path / "persist.db")
    conn.execute("DROP TRIGGER fail_inv"); conn.commit(); conn.close()
    store.complete_inference(identity["identity_key"], {"status": "ok", "output": {"a": 1}}, "completed")
    assert store.get_investigation(identity["investigation_id"])["status"] == "ok"
    assert store.get_inference(identity["identity_key"])["attempt_history"][0]["state"] == "completed"


def test_concurrent_attempts_have_single_attempt_history(tmp_path, monkeypatch):
    provider = FakeProvider(delay=0.4)
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "conc.db"))
    monkeypatch.setattr(app_module, "get_provider", lambda *a, **k: provider)
    app = create_app()
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: app.test_client().post(URL), range(8)))
    assert provider.calls == 1
    inv_id = responses[0].get_json()["investigation_id"]
    history = Store(tmp_path / "conc.db").list_inference_attempts(investigation_id=inv_id)
    assert len(history) == 1 and history[0]["state"] == "completed"


def _metrics_and_investigation(client, scenario, at_text):
    metrics = client.get("/api/metrics", query_string={"scenario": scenario, "at": at_text})
    investigation = client.get("/api/investigation", query_string={"scenario": scenario, "at": at_text})
    assert metrics.status_code == 200, metrics.get_json()
    assert investigation.status_code == 200, investigation.get_json()
    return metrics.get_json(), investigation.get_json()


def test_metrics_investigation_readiness_parity_video(tmp_path, monkeypatch):
    client, _ = _client(tmp_path, monkeypatch, FakeProvider())
    metrics, investigation = _metrics_and_investigation(client, "demo_video_v1", "2026-01-16T22:01:00-05:00")
    assert metrics["readiness"]["target_at_arrival"] == "met"
    assert investigation["readiness"]["target_at_arrival"] == "met"
    assert metrics["readiness"] == investigation["readiness"]
    assert metrics["computed_readiness"] == investigation["computed_readiness"]


def test_readiness_arrival_cases_and_rewind(tmp_path, monkeypatch):
    client, _ = _client(tmp_path, monkeypatch, FakeProvider())
    for at_text, expected_status, expected_target in [
        ("2026-01-16T20:30:00-05:00", "on_track", None),
        ("2026-01-16T21:00:00-05:00", "on_track", None),
        ("2026-01-16T22:01:00-05:00", "arrival_passed", "met"),
        ("2026-01-16T20:30:00-05:00", "on_track", None),
        ("2026-01-16T22:01:00-05:00", "arrival_passed", "met"),
    ]:
        metrics, investigation = _metrics_and_investigation(client, "demo_video_v1", at_text)
        assert metrics["readiness"]["status"] == expected_status
        assert metrics["readiness"]["target_at_arrival"] == expected_target
        assert metrics["readiness"] == investigation["readiness"]

    scenario = load_scenario(SCENARIOS / "demo_video_v1")
    at = datetime.fromisoformat("2026-01-16T21:30:00-05:00")
    after_only = copy.deepcopy(scenario)
    for record in after_only.records:
        if record.quantity == "indoor_temp" and record.observed_at > datetime.fromisoformat("2026-01-16T21:00:00-05:00"):
            record.value = 50.0
    assert build_evidence_pack(after_only, at)["canonical_readiness"]["target_at_arrival"] == "met"

    delayed = copy.deepcopy(scenario)
    arrival = datetime.fromisoformat("2026-01-16T21:00:00-05:00")
    for record in delayed.records:
        if record.quantity == "indoor_temp" and record.observed_at >= datetime.fromisoformat("2026-01-16T19:50:00-05:00"):
            record.received_at = arrival + timedelta(minutes=5)
    assert build_evidence_pack(delayed, at)["canonical_readiness"]["target_at_arrival"] == "unknown"

    missing = copy.deepcopy(scenario)
    missing.records = [r for r in missing.records if not (r.quantity == "indoor_temp" and datetime.fromisoformat("2026-01-16T20:40:00-05:00") <= r.observed_at <= arrival)]
    assert build_evidence_pack(missing, at)["canonical_readiness"]["target_at_arrival"] == "unknown"


def test_parity_every_shipped_scenario(tmp_path, monkeypatch):
    client, _ = _client(tmp_path, monkeypatch, FakeProvider())
    for scenario_dir in sorted(p for p in SCENARIOS.iterdir() if (p / "manifest.json").is_file()):
        scenario = load_scenario(scenario_dir)
        times = {scenario.manifest.start + timedelta(hours=1), scenario.manifest.start + timedelta(hours=3)}
        ctx_trip = scenario.trip
        if ctx_trip is not None:
            times.add(ctx_trip.planned_arrival - timedelta(minutes=30))
            times.add(ctx_trip.planned_arrival + timedelta(minutes=31))
        for moment in sorted(times):
            metrics, investigation = _metrics_and_investigation(client, scenario.manifest.id, moment.isoformat())
            assert metrics["readiness"] == investigation["readiness"], (scenario.manifest.id, moment)
            assert metrics["readiness"]["target_at_arrival"] == investigation["readiness"]["target_at_arrival"]
