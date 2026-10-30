"""Provider-error passthrough for the anomaly watcher.

A live watcher failure (timeout, auth, bad HTTP status, model mismatch,
...) must be recorded under its real name instead of being masked as
"no text block in reply (thinking only)". That reason is reserved for a
reply that really had no text block.
"""
import json
from datetime import datetime
from pathlib import Path

import scripts.record_care_watcher as rcw
from aria_home.scenario import load_scenario
from aria_home.watcher import (
    NO_TEXT_REASON,
    WATCHER_MODEL_ID,
    WATCHER_PROMPT_VERSION,
    is_provider_error_rejection,
    is_unreadable_rejection,
    provider_error_reason,
    request_live_watcher,
    run_watcher,
    watcher_identity,
)

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"
AT = datetime.fromisoformat("2026-01-17T02:31:00-05:00")
ENV = {
    "ARIA_HOME_MODEL_ENABLED": "1",
    "ARIA_HOME_PROVIDER_URL": "https://api.meta.ai",
    "ARIA_HOME_MODEL_ID": "muse-spark-1.3",
    "MODEL_API_KEY": "test-key",
}


def _care():
    return load_scenario(SCENARIOS_DIR / "care_home_v1")


class _ErrorProvider:
    mode = "live"
    model_id = WATCHER_MODEL_ID

    def __init__(self, payload):
        self.payload = dict(payload)
        self.calls = 0

    def generate(self, prompt=None, **kwargs):
        self.calls += 1
        return dict(self.payload)


def _failed_checks(payload):
    result = run_watcher(_care(), AT, _ErrorProvider(payload))
    assert result["final_result"] == "rejected"
    assert result["observations"] == []
    assert result["lowers_risk"] is False
    return result["failed_checks"]


def test_timeout_names_the_real_reason():
    checks = _failed_checks({"text": None, "error": "timeout", "mode": "live"})
    assert checks == ["provider error: timeout"]


def test_server_error_names_the_real_reason():
    checks = _failed_checks({"text": None, "error": "server_error", "mode": "live"})
    assert checks == ["provider error: server_error"]


def test_auth_names_the_real_reason():
    checks = _failed_checks({"text": None, "error": "auth", "mode": "live"})
    assert checks == ["provider error: auth"]


def test_bad_response_carries_the_http_status():
    checks = _failed_checks({"text": None, "error": "bad_response", "status": 402, "mode": "live"})
    assert checks == ["provider error: bad_response (HTTP 402)"]


def test_model_mismatch_carries_the_reply_model():
    checks = _failed_checks(
        {"text": None, "error": "model_mismatch", "model": "rogue-model", "status": 200, "mode": "live"}
    )
    assert checks == ["provider error: model_mismatch (reply model 'rogue-model')"]


def test_genuine_no_text_keeps_the_thinking_only_reason():
    for payload in (
        {"text": None, "mode": "live"},
        {"text": None, "error": None, "mode": "live"},
        {"text": None, "error": "no_text", "mode": "live"},
        {"text": None, "error": NO_TEXT_REASON, "mode": "live"},
    ):
        checks = _failed_checks(payload)
        assert checks == [NO_TEXT_REASON]
        assert not any(check.startswith("provider error:") for check in checks)


def test_provider_error_reason_formats_status_and_model():
    assert provider_error_reason({"error": "timeout", "status": None, "reply_model": None}) == "provider error: timeout"
    assert provider_error_reason({"error": "bad_response", "status": 402, "reply_model": None}) == "provider error: bad_response (HTTP 402)"
    assert provider_error_reason({"error": "model_mismatch", "status": 200, "reply_model": "rogue"}) == "provider error: model_mismatch (reply model 'rogue')"


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeClient:
    def __init__(self, status_code, payload):
        self._status = status_code
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, *args, **kwargs):
        return _FakeResponse(self._status, self._payload)


def test_request_live_watcher_reports_http_status_on_bad_response(monkeypatch):
    import aria_home.watcher as watcher

    monkeypatch.setattr(watcher.httpx, "Client", lambda timeout=None: _FakeClient(402, {"error": {"code": 402}}))
    assert request_live_watcher("{}", env=dict(ENV)) == {
        "ok": False, "error": "bad_response", "status": 402, "text": None,
    }


def test_request_live_watcher_reports_reply_model_on_mismatch(monkeypatch):
    import aria_home.watcher as watcher

    body = {"model": "rogue-model", "content": [{"type": "text", "text": "{}"}]}
    monkeypatch.setattr(watcher.httpx, "Client", lambda timeout=None: _FakeClient(200, body))
    assert request_live_watcher("{}", env=dict(ENV)) == {
        "ok": False, "error": "model_mismatch", "model": "rogue-model", "status": 200, "text": None,
    }


def test_request_live_watcher_model_check_matches_provider_allowlist():
    from aria_home.provider import ALLOWED_MODEL_IDS

    assert "muse-spark-1.3" in ALLOWED_MODEL_IDS
    env = dict(ENV, ARIA_HOME_MODEL_ID="gpt-x")
    assert request_live_watcher("{}", env=env) == {"ok": False, "error": "model_mismatch", "text": None}


def test_live_recorder_provider_passes_the_error_through(monkeypatch):
    live = {"ok": False, "error": "bad_response", "status": 402, "model": None, "text": None}
    monkeypatch.setattr(rcw, "request_live_watcher", lambda *args, **kwargs: dict(live))
    provider = rcw._LiveWatcherProvider({"MODEL_API_KEY": "k"}, 180.0, 4096)
    generated = provider.generate("prompt")
    assert generated["text"] is None
    assert generated["error"] == "bad_response"
    assert generated["status"] == 402
    outcome = run_watcher(_care(), AT, provider)
    assert outcome["final_result"] == "rejected"
    assert outcome["failed_checks"] == ["provider error: bad_response (HTTP 402)"]


def test_live_recorder_provider_keeps_the_reply_model(monkeypatch):
    live = {"ok": False, "error": "model_mismatch", "model": "rogue-model", "status": 200, "text": None}
    monkeypatch.setattr(rcw, "request_live_watcher", lambda *args, **kwargs: dict(live))
    provider = rcw._LiveWatcherProvider({"MODEL_API_KEY": "k"}, 180.0, 4096)
    assert provider.generate("prompt")["answered_model"] == "rogue-model"


def test_is_provider_error_rejection_only_matches_provider_errors():
    assert is_provider_error_rejection({"final_result": "rejected", "failed_checks": ["provider error: timeout"]}) is True
    assert is_provider_error_rejection({"final_result": "rejected", "failed_checks": ["provider error: bad_response (HTTP 402)"]}) is True
    assert is_provider_error_rejection({"final_result": "rejected", "failed_checks": [NO_TEXT_REASON]}) is False
    assert is_provider_error_rejection({"final_result": "rejected", "failed_checks": ["observation value does not match evidence r1"]}) is False
    assert is_provider_error_rejection({"final_result": "rejected", "failed_checks": ["provider error: timeout", "law x: y"]}) is False
    assert is_provider_error_rejection({"final_result": "confirmed", "failed_checks": []}) is False


def _seed_watchers(watchers_dir, failed_checks):
    scenario = load_scenario(rcw.SCENARIOS_DIR / rcw.CARE_SCENARIO_ID)
    recorded = []
    for item in rcw._plan(scenario):
        identity = item["identity"]
        recorded.append({
            "scenario_id": rcw.CARE_SCENARIO_ID,
            "evaluated_at_utc": identity["evaluated_at_utc"],
            "input_revision": identity["input_revision"],
            "laws_version": identity["laws_version"],
            "watcher_prompt_version": WATCHER_PROMPT_VERSION,
            "model_id": WATCHER_MODEL_ID,
            "provider_route": "meta live via Meta Model API (messages)",
            "code_snapshot": "seed",
            "recorded_at": "2026-10-30T19:03:25.476706+00:00",
            "status": "rejected",
            "final_result": "rejected",
            "failed_checks": list(failed_checks),
            "output": {"raw_text": "watcher returned no parseable JSON"},
        })
    watchers_dir.mkdir(parents=True, exist_ok=True)
    (watchers_dir / "watchers-care-2026-10-30.json").write_text(json.dumps({"watchers": recorded}), encoding="utf-8")


def test_only_missing_rerecords_provider_error_rejection(tmp_path):
    _seed_watchers(tmp_path / "watchers", ["provider error: bad_response (HTTP 402)"])
    scenario = load_scenario(rcw.SCENARIOS_DIR / rcw.CARE_SCENARIO_ID)
    needed, skipped = rcw._missing_plan(rcw._plan(scenario), tmp_path / "watchers")
    assert len(needed) == 8 and skipped == 0
    assert is_unreadable_rejection({"final_result": "rejected", "failed_checks": ["provider error: bad_response (HTTP 402)"]}) is False


def test_only_missing_keeps_mixed_provider_and_code_rejection(tmp_path):
    _seed_watchers(tmp_path / "watchers", ["provider error: timeout", "observation value does not match evidence r1"])
    scenario = load_scenario(rcw.SCENARIOS_DIR / rcw.CARE_SCENARIO_ID)
    needed, skipped = rcw._missing_plan(rcw._plan(scenario), tmp_path / "watchers")
    assert needed == [] and skipped == 8
