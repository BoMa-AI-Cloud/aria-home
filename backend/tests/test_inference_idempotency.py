import copy
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import aria_home.app as app_module
from aria_home.app import create_app
from aria_home.provider import MockProvider, ProviderResult
from aria_home.scenario import load_scenario
from pathlib import Path

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "demo_v1"
AT = "2026-01-16T18:00:00-05:00"
URL = f"/api/investigations?scenario=demo_v1&at={AT}"


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
    app = create_app()
    return app


def test_two_identical_posts_call_provider_once(tmp_path, monkeypatch):
    provider = CountingProvider()
    client = _app(tmp_path, monkeypatch, provider).test_client()
    r1 = client.post(URL)
    r2 = client.post(URL)
    assert r1.status_code == 200, r1.get_json()
    assert r2.status_code == 200, r2.get_json()
    assert r1.get_json()["investigation_id"] == r2.get_json()["investigation_id"]
    assert r2.get_json()["investigation"] == r1.get_json()["investigation"]
    assert provider.calls == 1


def test_concurrent_identical_posts_call_provider_once(tmp_path, monkeypatch):
    provider = CountingProvider(delay=0.5)
    app = _app(tmp_path, monkeypatch, provider)

    def post(_):
        return app.test_client().post(URL)

    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(post, range(8)))
    codes = sorted(r.status_code for r in responses)
    assert provider.calls == 1, codes
    assert codes == [200] + [202] * 7, codes
    for r in responses:
        if r.status_code == 202:
            body = r.get_json()
            assert body["status"] == "pending"
            assert body["investigation_id"]
    ids = {r.get_json()["investigation_id"] for r in responses}
    assert len(ids) == 1
    # after the owner finishes, an identical request returns the stored result
    r = app.test_client().post(URL)
    assert r.status_code == 200
    assert provider.calls == 1


def test_changed_time_or_input_gives_new_call(tmp_path, monkeypatch):
    provider = CountingProvider()
    client = _app(tmp_path, monkeypatch, provider).test_client()
    assert client.post(URL).status_code == 200
    assert provider.calls == 1
    later = "/api/investigations?scenario=demo_v1&at=2026-01-16T18:05:00-05:00"
    assert client.post(later).status_code == 200
    assert provider.calls == 2
    # different scenario input at the same time is a different identity
    other = f"/api/investigations?scenario=demo_recovery_v1&at={AT}"
    assert client.post(other).status_code == 200
    assert provider.calls == 3

    # a mutated visible record changes input_revision and the identity
    from aria_home.investigator import inference_identity
    scenario = load_scenario(SCENARIO_DIR)
    at = scenario.manifest.start + timedelta(hours=3)
    base = inference_identity(scenario, at)
    mutated = copy.deepcopy(scenario)
    for record in mutated.records:
        if record.received_at <= at and isinstance(record.value, (int, float)) and not isinstance(record.value, bool):
            record.value = float(record.value) + 100.0
            break
    changed = inference_identity(mutated, at)
    assert changed["input_revision"] != base["input_revision"]
    assert changed["identity_key"] != base["identity_key"]
    assert changed["investigation_id"] != base["investigation_id"]
    # equivalent instant expressed in UTC has the same identity
    from datetime import timezone
    assert inference_identity(scenario, at.astimezone(timezone.utc))["identity_key"] == base["identity_key"]


def test_failure_no_silent_retry_and_explicit_retry(tmp_path, monkeypatch):
    provider = CountingProvider(fail=True)
    client = _app(tmp_path, monkeypatch, provider).test_client()
    r1 = client.post(URL)
    assert provider.calls == 1
    assert r1.get_json()["investigation"]["status"] == "unavailable"
    r2 = client.post(URL)
    assert provider.calls == 1
    assert r2.get_json()["investigation_id"] == r1.get_json()["investigation_id"]
    assert r2.get_json()["investigation"]["status"] == "unavailable"

    provider.fail = False
    r3 = client.post(URL + "&retry=true")
    assert provider.calls == 2
    assert r3.status_code == 200
    assert r3.get_json()["investigation"]["status"] == "ok"
    r4 = client.post(URL)
    assert provider.calls == 2
    assert r4.get_json()["investigation"]["status"] == "ok"


def test_restarted_store_returns_stored_result(tmp_path, monkeypatch):
    provider = CountingProvider()
    client = _app(tmp_path, monkeypatch, provider).test_client()
    r1 = client.post(URL)
    assert r1.status_code == 200
    assert provider.calls == 1

    app2 = _app(tmp_path, monkeypatch, provider)
    r2 = app2.test_client().post(URL)
    assert r2.status_code == 200
    assert provider.calls == 1
    assert r2.get_json()["investigation_id"] == r1.get_json()["investigation_id"]
    assert r2.get_json()["investigation"] == r1.get_json()["investigation"]
