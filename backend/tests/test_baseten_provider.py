import json
import logging
import socket

import httpx
import pytest

from aria_home.evaluation import check_live_allowed, main
from aria_home.provider import (
    BasetenConfig,
    BasetenProvider,
    MetaProvider,
    MockProvider,
    get_provider,
)

FAKE_KEY = "TEST-BASETEN-NOT-A-REAL-KEY"
MODEL = "meta-models/muse-spark-open-1026"
BASE_ENV = {
    "BASETEN_API_KEY": FAKE_KEY,
    "ARIA_HOME_BASETEN_MODEL_ID": MODEL,
    "ARIA_HOME_BASETEN_ENABLED": "1",
}


@pytest.fixture(autouse=True)
def _block_socket(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("network socket use attempted")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def make_config(**overrides):
    data = {"api_key": FAKE_KEY, "model_id": MODEL, "enabled": True}
    data.update(overrides)
    return BasetenConfig(**data)


def counting_transport(handler):
    calls = {"count": 0, "requests": []}

    def _handler(request):
        calls["count"] += 1
        calls["requests"].append(request)
        return handler(request)

    return httpx.MockTransport(_handler), calls


def test_success_parses_text_and_tokens():
    def handler(request):
        assert str(request.url) == "https://inference.baseten.co/v1/chat/completions"
        assert request.headers["Authorization"] == f"Bearer {FAKE_KEY}"
        body = json.loads(request.content)
        assert body["model"] == MODEL
        assert body["messages"] == [{"role": "user", "content": "hello"}]
        return httpx.Response(
            200,
            json={
                "model": MODEL,
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "hi there", "reasoning_content": "thinking first"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
            },
        )

    transport, calls = counting_transport(handler)
    result = BasetenProvider(make_config(), transport=transport).generate("hello")
    assert calls["count"] == 1
    assert result.ok is True
    assert result.mode == "live"
    assert result.requested_model == MODEL
    assert result.answered_model == MODEL
    assert result.text == "hi there"
    assert result.input_tokens == 11
    assert result.output_tokens == 7
    assert result.stop_reason == "stop"
    assert result.error is None
    assert result.latency_ms >= 0
    assert FAKE_KEY not in result.model_dump_json()


def test_success_separates_reasoning_field():
    transport, _ = counting_transport(
        lambda request: httpx.Response(
            200,
            json={
                "model": MODEL,
                "choices": [{"message": {"content": "final", "reasoning": "secret chain"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 600},
            },
        )
    )
    result = BasetenProvider(make_config(), transport=transport).generate("x")
    assert result.ok is True
    assert result.text == "final"
    assert "secret chain" not in result.text


def test_reasoning_only_response_gives_no_text():
    transport, _ = counting_transport(
        lambda request: httpx.Response(
            200,
            json={
                "model": MODEL,
                "choices": [{"message": {"content": "", "reasoning_content": "still reasoning"}, "finish_reason": "length"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 256},
            },
        )
    )
    result = BasetenProvider(make_config(), transport=transport).generate("x")
    assert result.ok is False
    assert result.error == "no_text"
    assert result.text is None
    assert result.stop_reason == "length"
    assert result.input_tokens == 5
    assert result.output_tokens == 256


def test_reasoning_content_list_only_gives_no_text():
    transport, _ = counting_transport(
        lambda request: httpx.Response(
            200,
            json={
                "model": MODEL,
                "choices": [
                    {
                        "message": {"content": [{"type": "reasoning", "text": "only thinking"}]},
                        "finish_reason": "length",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 10},
            },
        )
    )
    result = BasetenProvider(make_config(), transport=transport).generate("x")
    assert result.ok is False
    assert result.error == "no_text"


def test_403_gives_auth_error():
    transport, _ = counting_transport(lambda request: httpx.Response(403, json={"error": "forbidden"}))
    result = BasetenProvider(make_config(), transport=transport).generate("x")
    assert result.ok is False
    assert result.error == "auth"
    assert FAKE_KEY not in result.model_dump_json()


def test_timeout_category():
    def handler(request):
        raise httpx.ReadTimeout("timed out", request=request)

    transport, calls = counting_transport(handler)
    result = BasetenProvider(make_config(), transport=transport).generate("x")
    assert calls["count"] == 1
    assert result.ok is False
    assert result.error == "timeout"
    assert result.text is None


def test_key_never_appears_in_error_string_or_log(caplog):
    transport, _ = counting_transport(lambda request: httpx.Response(403, json={"error": FAKE_KEY}))
    with caplog.at_level(logging.DEBUG):
        result = BasetenProvider(make_config(), transport=transport).generate("x")
    assert FAKE_KEY not in (result.error or "")
    assert FAKE_KEY not in result.model_dump_json()
    assert FAKE_KEY not in caplog.text
    transport2, _ = counting_transport(lambda request: httpx.Response(500, json={"error": FAKE_KEY}))
    result2 = BasetenProvider(make_config(), transport=transport2).generate("x")
    assert result2.error == "server_error"
    assert FAKE_KEY not in result2.model_dump_json()


def test_disabled_and_missing_key_make_zero_requests():
    transport, calls = counting_transport(lambda request: httpx.Response(200, json={}))
    assert BasetenProvider(make_config(enabled=False), transport=transport).generate("x").error == "disabled"
    assert BasetenProvider(make_config(api_key=None), transport=transport).generate("x").error == "not_configured"
    assert calls["count"] == 0


def test_env_config_defaults():
    config = BasetenConfig.from_env({"BASETEN_API_KEY": FAKE_KEY, "ARIA_HOME_BASETEN_ENABLED": "1"})
    assert config.model_id == MODEL
    assert config.base_url == "https://inference.baseten.co/v1"
    assert config.enabled is True
    assert config.api_key == FAKE_KEY
    assert FAKE_KEY not in repr(config)


def test_disallowed_baseten_model_rejected():
    with pytest.raises(ValueError, match="disallowed Baseten model id"):
        make_config(model_id="some-other-model")


def test_cli_refuses_without_enable_flag():
    with pytest.raises(RuntimeError):
        check_live_allowed(True, 1, env={"BASETEN_API_KEY": FAKE_KEY}, provider="baseten")
    assert check_live_allowed(True, 1, env=BASE_ENV, provider="baseten") is True
    with pytest.raises(SystemExit):
        main(["--live", "--provider", "baseten", "--max-calls", "1"], env={"BASETEN_API_KEY": FAKE_KEY})
    with pytest.raises(SystemExit):
        main(["--provider", "baseten", "--max-calls", "1"], env=BASE_ENV)
    with pytest.raises(SystemExit):
        main(["--live", "--provider", "baseten"], env=BASE_ENV)


def test_app_runtime_never_selects_baseten():
    env = {
        **BASE_ENV,
        "ARIA_HOME_PROVIDER_URL": "https://provider.example",
        "ARIA_HOME_MODEL_ID": "muse-spark-1.3",
        "MODEL_API_KEY": "meta-key",
        "ARIA_HOME_MODEL_ENABLED": "0",
    }
    provider = get_provider(env)
    assert isinstance(provider, MockProvider)
    assert not isinstance(provider, BasetenProvider)
    env_live = {**env, "ARIA_HOME_MODEL_ENABLED": "1"}
    provider_live = get_provider(env_live)
    assert isinstance(provider_live, MetaProvider)
    assert not isinstance(provider_live, BasetenProvider)
