import pathlib

import httpx
import pytest

from aria_home.app import create_app
from aria_home.provider import (
    ALLOWED_MODEL_IDS,
    MetaProvider,
    MockProvider,
    ProviderConfig,
    ProviderResult,
    get_provider,
)

FAKE_KEY = "TEST-NOT-A-REAL-KEY"
BASE_ENV = {
    "ARIA_HOME_PROVIDER_URL": "https://provider.example",
    "ARIA_HOME_MODEL_ID": "muse-spark-1.3",
    "MODEL_API_KEY": FAKE_KEY,
    "ARIA_HOME_MODEL_ENABLED": "1",
}


def make_config(**overrides):
    data = {
        "provider_url": "https://provider.example",
        "model_id": "muse-spark-1.3",
        "api_key": FAKE_KEY,
        "enabled": True,
    }
    data.update(overrides)
    return ProviderConfig(**data)


def counting_transport(handler):
    calls = {"count": 0, "requests": []}

    def _handler(request):
        calls["count"] += 1
        calls["requests"].append(request)
        return handler(request)

    return httpx.MockTransport(_handler), calls


def test_success():
    def handler(request):
        assert request.url == "https://provider.example/v1/messages"
        assert request.headers["Authorization"] == f"Bearer {FAKE_KEY}"
        import json

        body = json.loads(request.content)
        assert body["model"] == "muse-spark-1.3"
        assert body["max_tokens"] == 256
        assert body["messages"] == [{"role": "user", "content": "hello"}]
        return httpx.Response(
            200,
            json={
                "model": "muse-spark-1.3",
                "content": [{"type": "text", "text": "hi there"}],
                "usage": {"input_tokens": 3, "output_tokens": 2},
            },
        )

    transport, calls = counting_transport(handler)
    result = MetaProvider(make_config(), transport=transport).generate("hello")
    assert calls["count"] == 1
    assert isinstance(result, ProviderResult)
    assert result.ok is True
    assert result.mode == "live"
    assert result.requested_model == "muse-spark-1.3"
    assert result.answered_model == "muse-spark-1.3"
    assert result.text == "hi there"
    assert result.input_tokens == 3
    assert result.output_tokens == 2
    assert result.error is None
    assert result.latency_ms >= 0
    assert FAKE_KEY not in result.model_dump_json()


def test_timeout():
    def handler(request):
        raise httpx.ReadTimeout("timed out", request=request)

    transport, calls = counting_transport(handler)
    result = MetaProvider(make_config(), transport=transport).generate("hello")
    assert calls["count"] == 1
    assert result.ok is False
    assert result.error == "timeout"
    assert result.text is None


@pytest.mark.parametrize("status,category", [(401, "auth"), (403, "auth"), (429, "rate_limited"), (500, "server_error"), (503, "server_error")])
def test_http_error_mapping(status, category):
    transport, _ = counting_transport(lambda request: httpx.Response(status, json={"error": "x"}))
    result = MetaProvider(make_config(), transport=transport).generate("hello")
    assert result.ok is False
    assert result.error == category


def test_401():
    transport, _ = counting_transport(lambda request: httpx.Response(401, json={}))
    assert MetaProvider(make_config(), transport=transport).generate("x").error == "auth"


def test_429():
    transport, _ = counting_transport(lambda request: httpx.Response(429, json={}))
    assert MetaProvider(make_config(), transport=transport).generate("x").error == "rate_limited"


def test_500():
    transport, _ = counting_transport(lambda request: httpx.Response(500, json={}))
    assert MetaProvider(make_config(), transport=transport).generate("x").error == "server_error"


def test_malformed_body():
    transport, _ = counting_transport(lambda request: httpx.Response(200, content=b"not-json"))
    result = MetaProvider(make_config(), transport=transport).generate("x")
    assert result.ok is False
    assert result.error == "bad_response"


def test_malformed_shape():
    transport, _ = counting_transport(lambda request: httpx.Response(200, json={"model": "muse-spark-1.3", "content": []}))
    result = MetaProvider(make_config(), transport=transport).generate("x")
    assert result.ok is False
    assert result.error == "bad_response"


def test_no_text_thinking_only():
    transport, _ = counting_transport(
        lambda request: httpx.Response(
            200,
            json={
                "model": "muse-spark-1.3",
                "content": [{"type": "thinking", "thinking": "planning silently"}],
                "stop_reason": "max_tokens",
                "usage": {"input_tokens": 5, "output_tokens": 1},
            },
        )
    )
    result = MetaProvider(make_config(), transport=transport).generate("x")
    assert result.ok is False
    assert result.error == "no_text"
    assert result.content_block_types == ["thinking"]
    assert result.stop_reason == "max_tokens"
    assert result.input_tokens == 5
    assert result.output_tokens == 1
    assert result.text is None


def test_thinking_plus_text_returns_text_only():
    transport, _ = counting_transport(
        lambda request: httpx.Response(
            200,
            json={
                "model": "muse-spark-1.3",
                "content": [
                    {"type": "thinking", "thinking": "planning silently"},
                    {"type": "text", "text": "final answer"},
                ],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 5, "output_tokens": 2},
            },
        )
    )
    result = MetaProvider(make_config(), transport=transport).generate("x")
    assert result.ok is True
    assert result.text == "final answer"
    assert result.content_block_types == ["thinking", "text"]
    assert result.stop_reason == "end_turn"


def test_model_mismatch():
    transport, _ = counting_transport(
        lambda request: httpx.Response(
            200,
            json={"model": "muse-wonder-1.0", "content": [{"type": "text", "text": "hi"}], "usage": {}},
        )
    )
    result = MetaProvider(make_config(), transport=transport).generate("x")
    assert result.ok is False
    assert result.error == "model_mismatch"
    assert result.answered_model == "muse-wonder-1.0"
    assert result.text is None


def test_missing_key_makes_zero_requests():
    transport, calls = counting_transport(lambda request: httpx.Response(200, json={}))
    result = MetaProvider(make_config(api_key=None), transport=transport).generate("x")
    assert calls["count"] == 0
    assert result.ok is False
    assert result.error == "not_configured"


def test_disabled_makes_zero_requests():
    transport, calls = counting_transport(lambda request: httpx.Response(200, json={}))
    result = MetaProvider(make_config(enabled=False), transport=transport).generate("x")
    assert calls["count"] == 0
    assert result.ok is False
    assert result.error == "disabled"


def test_disallowed_model_id_rejected():
    assert ALLOWED_MODEL_IDS == {"muse-spark-1.3", "muse-wonder-1.0"}
    with pytest.raises(ValueError, match="disallowed model id"):
        make_config(model_id="some-other-model")
    with pytest.raises(ValueError, match="disallowed model id"):
        ProviderConfig(provider_url="https://x", model_id="gpt-4", api_key=FAKE_KEY, enabled=True)
    with pytest.raises(ValueError, match="disallowed model id"):
        get_provider({**BASE_ENV, "ARIA_HOME_MODEL_ID": "claude-sonnet-5-5"})


def test_mock_text_label_present():
    result = MockProvider().generate("anything")
    assert result.ok is True
    assert result.mode == "mock"
    assert result.text.startswith("[MOCK - not live inference]")
    assert MockProvider().generate("a").text == MockProvider().generate("b").text


def test_get_provider_defaults_to_mock():
    assert isinstance(get_provider({}), MockProvider)
    assert isinstance(get_provider({**BASE_ENV, "ARIA_HOME_MODEL_ENABLED": "0"}), MockProvider)
    assert isinstance(get_provider({k: v for k, v in BASE_ENV.items() if k != "MODEL_API_KEY"}), MetaProvider)
    assert isinstance(get_provider(BASE_ENV), MetaProvider)


def test_api_provider_never_contains_key(monkeypatch):
    for key, value in BASE_ENV.items():
        monkeypatch.setenv(key, value)
    client = create_app().test_client()
    resp = client.get("/api/provider")
    assert resp.status_code == 200
    body_text = resp.get_data(as_text=True)
    assert FAKE_KEY not in body_text
    body = resp.get_json()
    assert body["mode"] == "live"
    assert body["model_id"] == "muse-spark-1.3"
    assert body["enabled"] is True
    assert body["key_present"] is True


def test_api_provider_mock_by_default(monkeypatch):
    for var in BASE_ENV:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("MODEL_API_KEY", FAKE_KEY)
    client = create_app().test_client()
    resp = client.get("/api/provider")
    assert FAKE_KEY not in resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["mode"] == "mock"
    assert body["enabled"] is False
    assert body["key_present"] is True


def test_lowercase_api_key_env_is_not_configured():
    config = ProviderConfig.from_env({"api_key": FAKE_KEY})
    assert config.api_key is None
    assert config.is_configured() is False
    assert isinstance(get_provider(config), MockProvider)


def test_app_config_never_reads_forbidden_key():
    package = pathlib.Path(__file__).resolve().parent.parent / "aria_home"
    source = "\n".join(p.read_text(encoding="utf-8") for p in sorted(package.glob("*.py")))
    forbidden = "META_" + "CLAUDE_CODE_KEY"
    assert forbidden not in source
    assert "ANTHROPIC_" not in source


def test_enabled_missing_key_returns_not_configured_with_zero_calls():
    env = {k: v for k, v in BASE_ENV.items() if k != "MODEL_API_KEY"}
    provider = get_provider(env)
    assert isinstance(provider, MetaProvider)
    transport, calls = counting_transport(lambda request: httpx.Response(200, json={}))
    provider.transport = transport
    result = provider.generate("x")
    assert calls["count"] == 0
    assert result.ok is False
    assert result.error == "not_configured"


def test_enabled_missing_url_returns_not_configured_with_zero_calls():
    env = {k: v for k, v in BASE_ENV.items() if k != "ARIA_HOME_PROVIDER_URL"}
    provider = get_provider(env)
    assert isinstance(provider, MetaProvider)
    transport, calls = counting_transport(lambda request: httpx.Response(200, json={}))
    provider.transport = transport
    result = provider.generate("x")
    assert calls["count"] == 0
    assert result.ok is False
    assert result.error == "not_configured"


def test_disabled_returns_mock():
    provider = get_provider({**BASE_ENV, "ARIA_HOME_MODEL_ENABLED": "0"})
    assert isinstance(provider, MockProvider)
    result = provider.generate("x")
    assert result.ok is True
    assert result.mode == "mock"


def test_api_provider_mock_config_error_null(monkeypatch):
    for var in BASE_ENV:
        monkeypatch.delenv(var, raising=False)
    client = create_app().test_client()
    resp = client.get("/api/provider")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["mode"] == "mock"
    assert body["config_error"] is None


def test_api_provider_config_error_lists_missing_names(monkeypatch):
    for key, value in BASE_ENV.items():
        if key != "MODEL_API_KEY":
            monkeypatch.setenv(key, value)
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    client = create_app().test_client()
    resp = client.get("/api/provider")
    assert resp.status_code == 200
    body_text = resp.get_data(as_text=True)
    assert FAKE_KEY not in body_text
    body = resp.get_json()
    assert body["mode"] == "live"
    assert body["configured"] is False
    assert body["config_error"] == ["MODEL_API_KEY"]


def test_api_provider_config_error_missing_url(monkeypatch):
    for key, value in BASE_ENV.items():
        if key != "ARIA_HOME_PROVIDER_URL":
            monkeypatch.setenv(key, value)
    monkeypatch.delenv("ARIA_HOME_PROVIDER_URL", raising=False)
    client = create_app().test_client()
    resp = client.get("/api/provider")
    assert resp.status_code == 200
    assert FAKE_KEY not in resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["mode"] == "live"
    assert body["configured"] is False
    assert body["config_error"] == ["ARIA_HOME_PROVIDER_URL"]
