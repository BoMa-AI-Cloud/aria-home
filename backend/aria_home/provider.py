"""Model-provider adapter for ARIA Home.

UNVERIFIED: confirm against Meta's official docs before the first live call

The live request below is implemented for a Messages-compatible API
(POST {base}/v1/messages, header "Authorization: Bearer <key>", JSON body
with model, max_tokens, messages). Runtime configuration comes from
environment variables only.
"""
import os
import time
from dataclasses import dataclass, field
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict

ALLOWED_MODEL_IDS = frozenset({"muse-spark-1.3", "muse-wonder-1.0"})
ALLOWED_MODELS = ALLOWED_MODEL_IDS
DEFAULT_MODEL_ID = "muse-spark-1.3"
DEFAULT_TIMEOUT_S = 20.0
DEFAULT_MAX_TOKENS = 256
MOCK_PREFIX = "[MOCK - not live inference]"

ErrorCategory = Literal[
    "not_configured",
    "disabled",
    "timeout",
    "auth",
    "rate_limited",
    "server_error",
    "bad_response",
    "model_mismatch",
]


def _validate_model_id(model_id):
    if model_id is not None and model_id not in ALLOWED_MODEL_IDS:
        raise ValueError(
            f"disallowed model id: {model_id!r}; "
            f"allowed model ids: {sorted(ALLOWED_MODEL_IDS)}"
        )
    return model_id


class ProviderResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    mode: Literal["mock", "live"]
    requested_model: str | None = None
    answered_model: str | None = None
    text: str | None = None
    latency_ms: float = 0.0
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: ErrorCategory | None = None


@dataclass(frozen=True)
class ProviderConfig:
    provider_url: str | None = None
    model_id: str | None = None
    api_key: str | None = field(default=None, repr=False)
    enabled: bool = False
    timeout_s: float = DEFAULT_TIMEOUT_S
    max_tokens: int = DEFAULT_MAX_TOKENS

    def __post_init__(self):
        _validate_model_id(self.model_id)

    @property
    def base_url(self):
        return self.provider_url

    @property
    def model(self):
        return self.model_id

    @property
    def timeout(self):
        return self.timeout_s

    @property
    def max_output_tokens(self):
        return self.max_tokens

    @property
    def configured(self):
        return bool(self.provider_url and self.model_id and self.api_key)

    def is_configured(self):
        return self.configured

    @classmethod
    def from_env(cls, env=None):
        source = os.environ if env is None else env
        get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
        if isinstance(source, cls):
            return source
        if not hasattr(source, "get") and not isinstance(source, dict):
            return cls(
                provider_url=getattr(source, "provider_url", None) or getattr(source, "base_url", None),
                model_id=getattr(source, "model_id", None) or getattr(source, "model", None),
                api_key=getattr(source, "api_key", None),
                enabled=bool(getattr(source, "enabled", False)),
                timeout_s=getattr(source, "timeout_s", None) or getattr(source, "timeout", None) or DEFAULT_TIMEOUT_S,
                max_tokens=getattr(source, "max_tokens", None) or getattr(source, "max_output_tokens", None) or DEFAULT_MAX_TOKENS,
            )
        provider_url = get("ARIA_HOME_PROVIDER_URL") or get("provider_url") or get("base_url") or get("ARIA_HOME_BASE_URL")
        model_id = get("ARIA_HOME_MODEL_ID") or get("model_id") or get("model")
        api_key = get("MODEL_API_KEY") or get("api_key")
        raw_enabled = get("ARIA_HOME_MODEL_ENABLED", get("enabled", False))
        enabled = raw_enabled == "1" or raw_enabled is True
        timeout_raw = get("timeout_s") or get("timeout") or DEFAULT_TIMEOUT_S
        max_raw = get("max_tokens") or get("max_output_tokens") or get("maxTokens") or DEFAULT_MAX_TOKENS
        if isinstance(provider_url, str):
            provider_url = provider_url.strip() or None
        if isinstance(model_id, str):
            model_id = model_id.strip() or None
        if isinstance(api_key, str):
            api_key = api_key.strip() or None
        return cls(
            provider_url=provider_url,
            model_id=model_id,
            api_key=api_key,
            enabled=enabled,
            timeout_s=float(timeout_raw),
            max_tokens=int(max_raw),
        )


ModelProviderConfig = ProviderConfig
MetaProviderConfig = ProviderConfig
Config = ProviderConfig


def _coerce_config(config=None, env=None):
    if isinstance(config, ProviderConfig):
        return config
    if config is None:
        return ProviderConfig.from_env(env)
    if isinstance(config, dict):
        has_env_keys = any(
            k in config
            for k in ("ARIA_HOME_PROVIDER_URL", "ARIA_HOME_MODEL_ID", "MODEL_API_KEY", "ARIA_HOME_MODEL_ENABLED")
        )
        if has_env_keys:
            return ProviderConfig.from_env(config)
        return ProviderConfig(
            provider_url=config.get("provider_url") or config.get("base_url") or config.get("url"),
            model_id=config.get("model_id") or config.get("model") or config.get("requested_model"),
            api_key=config.get("api_key") or config.get("key"),
            enabled=config.get("enabled", False) in (True, "1", 1),
            timeout_s=float(config.get("timeout_s") or config.get("timeout") or DEFAULT_TIMEOUT_S),
            max_tokens=int(config.get("max_tokens") or config.get("max_output_tokens") or DEFAULT_MAX_TOKENS),
        )
    return ProviderConfig.from_env(config)


def _normalize_messages(prompt=None, messages=None):
    if messages is not None:
        return messages
    if isinstance(prompt, list):
        return prompt
    if prompt is None:
        return [{"role": "user", "content": ""}]
    return [{"role": "user", "content": str(prompt)}]


def build_request(config, messages):
    base = (config.provider_url or "").rstrip("/")
    return {
        "url": f"{base}/v1/messages",
        "headers": {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        "json": {
            "model": config.model_id,
            "max_tokens": config.max_tokens,
            "messages": messages,
        },
    }


_build_request = build_request


class MockProvider:
    def __init__(self, model_id=None, requested_model=None, config=None):
        resolved = requested_model or model_id
        if config is not None:
            resolved = resolved or _coerce_config(config).model_id
        self.model_id = _validate_model_id(resolved) or DEFAULT_MODEL_ID
        self.requested_model = self.model_id
        self.mode = "mock"

    def generate(self, prompt=None, *, messages=None, max_tokens=None):
        return ProviderResult(
            ok=True,
            mode="mock",
            requested_model=self.model_id,
            answered_model=self.model_id,
            text=f"{MOCK_PREFIX} This is a canned ARIA Home mock response.",
            latency_ms=0.0,
            input_tokens=None,
            output_tokens=None,
            error=None,
        )

    complete = generate
    chat = generate
    __call__ = generate


class MetaProvider:
    mode = "live"

    def __init__(self, config=None, transport=None, *, timeout=None, timeout_s=None, max_tokens=None, max_output_tokens=None, env=None):
        self.config = _coerce_config(config, env=env)
        _validate_model_id(self.config.model_id)
        self.transport = transport
        resolved_timeout = timeout if timeout is not None else timeout_s
        self.timeout_s = float(resolved_timeout) if resolved_timeout is not None else float(self.config.timeout_s)
        resolved_max = max_tokens if max_tokens is not None else max_output_tokens
        self.max_tokens = int(resolved_max) if resolved_max is not None else int(self.config.max_tokens)
        if resolved_max is not None and isinstance(self.config, ProviderConfig):
            object.__setattr__(self.config, "max_tokens", self.max_tokens)

    @property
    def model_id(self):
        return self.config.model_id

    def generate(self, prompt=None, *, messages=None, max_tokens=None):
        start = time.perf_counter()

        def elapsed():
            return (time.perf_counter() - start) * 1000.0

        def fail(category, answered_model=None):
            return ProviderResult(
                ok=False,
                mode="live",
                requested_model=self.config.model_id,
                answered_model=answered_model,
                text=None,
                latency_ms=elapsed(),
                input_tokens=None,
                output_tokens=None,
                error=category,
            )

        if not self.config.enabled:
            return fail("disabled")
        if not self.config.api_key:
            return fail("not_configured")
        if not self.config.provider_url or not self.config.model_id:
            return fail("not_configured")
        _validate_model_id(self.config.model_id)

        effective_config = self.config
        if max_tokens is not None:
            effective_config = ProviderConfig(
                provider_url=self.config.provider_url,
                model_id=self.config.model_id,
                api_key=self.config.api_key,
                enabled=self.config.enabled,
                timeout_s=self.config.timeout_s,
                max_tokens=int(max_tokens),
            )
        elif self.max_tokens != self.config.max_tokens:
            effective_config = ProviderConfig(
                provider_url=self.config.provider_url,
                model_id=self.config.model_id,
                api_key=self.config.api_key,
                enabled=self.config.enabled,
                timeout_s=self.config.timeout_s,
                max_tokens=self.max_tokens,
            )

        request = build_request(effective_config, _normalize_messages(prompt, messages))
        try:
            with httpx.Client(transport=self.transport, timeout=self.timeout_s) as client:
                response = client.post(request["url"], headers=request["headers"], json=request["json"])
        except httpx.TimeoutException:
            return fail("timeout")
        except httpx.HTTPError:
            return fail("server_error")

        status = response.status_code
        if status in (401, 403):
            return fail("auth")
        if status == 429:
            return fail("rate_limited")
        if 500 <= status <= 599:
            return fail("server_error")
        if not 200 <= status <= 299:
            return fail("bad_response")

        try:
            body = response.json()
        except ValueError:
            return fail("bad_response")
        if not isinstance(body, dict):
            return fail("bad_response")

        answered_model = body.get("model")
        if not isinstance(answered_model, str) or not answered_model:
            return fail("bad_response")
        if answered_model != self.config.model_id:
            return fail("model_mismatch", answered_model=answered_model)

        content = body.get("content")
        if not isinstance(content, list):
            return fail("bad_response", answered_model=answered_model)
        parts = [
            block["text"]
            for block in content
            if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)
        ]
        if not parts:
            return fail("bad_response", answered_model=answered_model)

        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        return ProviderResult(
            ok=True,
            mode="live",
            requested_model=self.config.model_id,
            answered_model=answered_model,
            text="".join(parts),
            latency_ms=elapsed(),
            input_tokens=input_tokens if isinstance(input_tokens, int) else None,
            output_tokens=output_tokens if isinstance(output_tokens, int) else None,
            error=None,
        )

    complete = generate
    chat = generate
    __call__ = generate


LiveProvider = MetaProvider


def get_provider(env=None):
    config = _coerce_config(env) if not isinstance(env, ProviderConfig) else env
    if isinstance(env, ProviderConfig):
        config = env
    elif env is not None and not isinstance(env, dict):
        config = _coerce_config(env)
    _validate_model_id(config.model_id)
    if not config.enabled or not config.configured:
        return MockProvider(model_id=config.model_id or DEFAULT_MODEL_ID)
    return MetaProvider(config)
