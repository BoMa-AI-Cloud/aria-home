"""Thinking-block sweeps: every reply reader skips thinking/redacted_thinking and reasoning."""
import json
from datetime import datetime
from pathlib import Path

import httpx

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"
AT = datetime.fromisoformat("2026-01-17T02:31:00-05:00")

WATCHER_JSON = json.dumps({"observations": [{
    "kind": "temperature_drop",
    "claim": "Room temp 52.0F at 02:30, 16.0F below 68F target with falling trend",
    "evidence_ids": ["tstat-temp-0230"],
    "values": {"value": 52.0, "unit": "F", "at": "2026-01-17T02:30:00-05:00"},
}]})
WATCHER_BODY = {
    "model": "muse-spark-1.3",
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 100, "output_tokens": 3509},
    "content": [
        {"type": "redacted_thinking", "data": "enc-thinking-bytes"},
        {"type": "text", "text": WATCHER_JSON},
    ],
}
THINKING_ONLY_BODY = {
    "model": "muse-spark-1.3",
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 100, "output_tokens": 3509},
    "content": [{"type": "redacted_thinking", "data": "enc-thinking-bytes"}],
}
ENV = {
    "ARIA_HOME_MODEL_ENABLED": "1",
    "ARIA_HOME_PROVIDER_URL": "https://api.meta.ai",
    "ARIA_HOME_MODEL_ID": "muse-spark-1.3",
    "MODEL_API_KEY": "test-key",
}


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self._status = status_code

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, *args, **kwargs):
        return _FakeResponse(self._status, self._payload)


def _care():
    from aria_home.scenario import load_scenario

    return load_scenario(SCENARIOS_DIR / "care_home_v1")


def test_watcher_live_skips_redacted_thinking(monkeypatch):
    import aria_home.watcher as watcher

    monkeypatch.setattr(watcher.httpx, "Client", lambda timeout=None: _FakeClient(WATCHER_BODY))
    result = watcher.request_live_watcher("{}", env=dict(ENV))
    assert result == {"ok": True, "error": None, "text": WATCHER_JSON}


def test_watcher_thinking_only_clear_reason(monkeypatch):
    import aria_home.watcher as watcher

    monkeypatch.setattr(watcher.httpx, "Client", lambda timeout=None: _FakeClient(THINKING_ONLY_BODY))
    result = watcher.request_live_watcher("{}", env=dict(ENV))
    assert result["ok"] is False
    assert result["text"] is None
    assert result["error"] == watcher.NO_TEXT_REASON

    class _Empty:
        mode = "live"
        model_id = "muse-spark-1.3"

        def generate(self, prompt=None, **kwargs):
            return {"text": None, "answered_model": self.model_id, "requested_model": self.model_id, "mode": "live"}

    outcome = watcher.run_watcher(_care(), AT, _Empty())
    assert outcome["final_result"] == "rejected"
    assert watcher.NO_TEXT_REASON in outcome["failed_checks"]
    assert not any("invalid JSON" in check for check in outcome["failed_checks"])


def test_provider_skips_redacted_thinking():
    from aria_home.provider import MetaProvider, ProviderConfig

    def handler(request):
        return httpx.Response(200, json=WATCHER_BODY)

    config = ProviderConfig(provider_url="https://api.meta.ai", model_id="muse-spark-1.3", api_key="k", enabled=True)
    result = MetaProvider(config, transport=httpx.MockTransport(handler)).generate("x")
    assert result.ok is True
    assert result.text == WATCHER_JSON


def test_investigator_skips_redacted_thinking():
    from aria_home.investigator import investigate
    from aria_home.provider import MetaProvider, MockProvider, ProviderConfig

    scenario = _care()
    mock_text = MockProvider().generate.__self__ and None
    probe = MockProvider(model_id="muse-spark-1.3")
    from aria_home.investigator import build_evidence_pack

    pack = build_evidence_pack(scenario, AT)
    import json as _json

    prompt = "inv-v3 Evidence pack (JSON):\n" + _json.dumps(pack)
    valid_text = probe.generate(prompt).text
    assert valid_text is not None

    def handler(request):
        return httpx.Response(200, json={
            "model": "muse-spark-1.3",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 1, "output_tokens": 2},
            "content": [
                {"type": "redacted_thinking", "data": "enc"},
                {"type": "text", "text": valid_text},
            ],
        })

    config = ProviderConfig(provider_url="https://api.meta.ai", model_id="muse-spark-1.3", api_key="k", enabled=True)
    live = MetaProvider(config, transport=httpx.MockTransport(handler))
    result = investigate(scenario, AT, provider=live)
    assert result.status == "ok"


def test_review_skips_reasoning_and_thinking():
    import json as _json

    from aria_home.review import parse_review_response

    review_json = _json.dumps({"verdict": "no_issues", "issues": []})
    data = {"output": [
        {"type": "reasoning", "id": "rs-1"},
        {"type": "message", "content": [
            {"type": "thinking", "text": "plan silently"},
            {"type": "redacted_thinking", "data": "enc"},
            {"type": "output_text", "text": review_json},
        ]},
    ]}
    parsed, reasons = parse_review_response(data, ["e1"])
    assert reasons == []
    assert parsed == {"verdict": "no_issues", "issues": []}


def test_visual_skips_thinking():
    from aria_home.visual import extract_sam_text

    response = {"output": [
        {"type": "reasoning", "content": [{"type": "text", "text": "should be skipped"}]},
        {"type": "message", "content": [
            {"type": "thinking", "text": "plan"},
            {"type": "redacted_thinking", "data": "enc"},
            {"type": "output_text", "text": "<0f>0<|box;x1=1;y1=2;x2=3;y2=4;w=10;h=10|>"},
        ]},
    ]}
    assert extract_sam_text(response) == "<0f>0<|box;x1=1;y1=2;x2=3;y2=4;w=10;h=10|>"


def test_transcribe_ignores_extra_reasoning():
    from aria_home.transcribe import parse_transcription_response

    payload = {
        "sessionId": "s1",
        "transcript": "furnace is off",
        "audioDurationMs": 1000,
        "turns": [],
        "reasoning_content": "should be ignored",
        "reasoning": "should be ignored",
    }
    transcript, reasons = parse_transcription_response(payload)
    assert reasons == []
    assert transcript["transcript"] == "furnace is off"


def test_scripts_watcher_provider_skips_redacted_thinking(monkeypatch):
    import aria_home.watcher as watcher
    import scripts.record_care_watcher as rcw

    monkeypatch.setattr(watcher.httpx, "Client", lambda timeout=None: _FakeClient(WATCHER_BODY))
    provider = rcw._LiveWatcherProvider(dict(ENV), 20.0, 512)
    result = provider.generate(WATCHER_JSON)
    assert result["text"] == WATCHER_JSON
    assert result["mode"] == "live"
