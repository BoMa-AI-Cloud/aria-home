"""Model-provider adapter for ARIA Home.

Status verified against https://dev.meta.ai/docs/coding-agents on 2026-10-26:
endpoint base host (https://api.meta.ai, no /v1 suffix), Messages path
(/v1/messages), auth ("Authorization: Bearer <key>"), and model IDs
(muse-wonder-1.0, muse-spark-1.3). One live call succeeded on 2026-10-26
16:54Z. The request body fields (model, max_tokens, messages) are NOT
verified against the API reference, which was not checked.

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
    "no_text",
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
    content_block_types: list[str] | None = None
    stop_reason: str | None = None


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

    def missing_settings(self):
        missing = []
        if not self.provider_url:
            missing.append("ARIA_HOME_PROVIDER_URL")
        if not self.model_id:
            missing.append("ARIA_HOME_MODEL_ID")
        if not self.api_key:
            missing.append("MODEL_API_KEY")
        return missing

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
        api_key = get("MODEL_API_KEY")
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
            api_key=config.get("api_key"),
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
        text_in = ""
        if isinstance(prompt, str):
            text_in = prompt
        elif messages:
            text_in = " ".join(str(m.get("content", "")) if isinstance(m, dict) else str(m) for m in messages)
        elif prompt is not None:
            text_in = str(prompt)
        if "inv-v2" in text_in:
            import json as _json
            from datetime import datetime as _dt, timedelta as _td

            pack, when = {}, "2026-01-16T18:30:00+00:00"
            marker = "Evidence pack (JSON):\n"
            if marker in text_in:
                try:
                    pack = _json.loads(text_in.split(marker, 1)[1])
                except Exception:
                    pack = {}
            elif "{" in text_in:
                try:
                    pack = _json.loads(text_in[text_in.index("{"):])
                except Exception:
                    pack = {}
            ids = pack.get("evidence_ids") or [e.get("id") for e in pack.get("evidence", []) if isinstance(e, dict) and e.get("id")]
            trend_id = "metric:indoor_trend" if "metric:indoor_trend" in ids else (ids[0] if ids else "metric:indoor_trend")
            power_id = "power:continuity" if "power:continuity" in ids else trend_id
            if pack.get("at"):
                try:
                    when = (_dt.fromisoformat(str(pack["at"]).replace("Z", "+00:00")) + _td(minutes=30)).isoformat()
                except Exception:
                    pass
            metrics = pack.get("metrics") or {}
            trend = metrics.get("indoor_trend") or {}
            gap = metrics.get("target_gap") or {}
            circuits = metrics.get("circuits") or {}
            facts = []
            if trend.get("last_value") is not None and trend.get("fresh", trend.get("is_fresh", True)):
                fact = {"claim_type": "current_temperature", "evidence_id": trend_id, "field": "last_value", "value": trend["last_value"], "unit": trend.get("unit") or "F", "at": trend.get("last_observed_at")}
                facts.append(fact)
            if gap.get("target_temp") is not None and "metric:target_gap" in ids:
                facts.append({"claim_type": "target_temperature", "evidence_id": "metric:target_gap", "field": "target_temp", "value": gap["target_temp"], "unit": gap.get("target_unit") or gap.get("unit") or "F", "at": gap.get("latest_observed_at")})
            if gap.get("gap") is not None and "metric:target_gap" in ids and trend.get("fresh", trend.get("is_fresh", True)):
                facts.append({"claim_type": "target_gap", "evidence_id": "metric:target_gap", "field": "gap", "value": gap["gap"], "unit": gap.get("unit") or "F", "at": gap.get("latest_observed_at")})
            circuit_id = next((cid for cid in sorted(circuits) if "furnace" in cid), None) or (sorted(circuits)[0] if circuits else None)
            if circuit_id is not None:
                circuit = circuits.get(circuit_id) or {}
                circuit_evidence = f"metric:circuit_activity:{circuit_id}"
                if circuit_evidence in ids and circuit.get("max_w") is not None and circuit.get("fresh", circuit.get("is_fresh", True)):
                    facts.append({"claim_type": "electrical_activity", "evidence_id": circuit_evidence, "field": "max_w", "value": circuit["max_w"], "unit": circuit.get("unit") or "W", "at": circuit.get("last_observed_at")})
                    facts.append({"claim_type": "equipment_function", "evidence_id": circuit_evidence, "field": "active", "value": "not_observed" if circuit.get("active") is False else "unknown", "unit": None, "at": circuit.get("last_observed_at")})
            if not facts:
                facts.append({"claim_type": "equipment_function", "evidence_id": trend_id, "field": "active", "value": "unknown", "unit": None, "at": None})
            payload = {
                "facts": facts,
                "interpretation": "[MOCK] The verified facts describe the indoor temperature relative to the target.",
                "hypotheses": [{"text": "[MOCK] The property may not yet be ready on arrival based on the cited trend.", "supporting_ids": [trend_id], "conflicting_ids": []}],
                "unknowns": ["Whether heating equipment is receiving power is not established by the cited evidence."],
                "clarification": "Who should respond first if the indoor temperature has not improved by the next check?",
                "follow_up": {"observation": "Take another indoor temperature reading and review the trend.", "when": when},
                "readiness": (pack.get("readiness") or {}).get("status") or pack.get("computed_readiness") or "cannot_tell",
                "limitations": ["Mock example only; not live inference."],
            }
            return ProviderResult(ok=True, mode="mock", requested_model=self.model_id, answered_model=self.model_id, text=_json.dumps(payload), latency_ms=0.0, input_tokens=None, output_tokens=None, error=None)
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

        def fail(category, answered_model=None, content_block_types=None, stop_reason=None, input_tokens=None, output_tokens=None):
            return ProviderResult(
                ok=False,
                mode="live",
                requested_model=self.config.model_id,
                answered_model=answered_model,
                text=None,
                latency_ms=elapsed(),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                error=category,
                content_block_types=content_block_types,
                stop_reason=stop_reason,
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

        raw_stop = body.get("stop_reason")
        stop_reason = raw_stop if isinstance(raw_stop, str) else None

        def block_types():
            content = body.get("content")
            if not isinstance(content, list):
                return None
            types = []
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("type"), str):
                    types.append(block["type"])
            return types

        def usage_tokens():
            usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
            raw_in = usage.get("input_tokens")
            raw_out = usage.get("output_tokens")
            return (
                raw_in if isinstance(raw_in, int) else None,
                raw_out if isinstance(raw_out, int) else None,
            )

        answered_model = body.get("model")
        if not isinstance(answered_model, str) or not answered_model:
            return fail("bad_response", content_block_types=block_types(), stop_reason=stop_reason)
        if answered_model != self.config.model_id:
            input_tokens, output_tokens = usage_tokens()
            return fail(
                "model_mismatch",
                answered_model=answered_model,
                content_block_types=block_types(),
                stop_reason=stop_reason,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        content = body.get("content")
        if not isinstance(content, list) or len(content) == 0:
            input_tokens, output_tokens = usage_tokens()
            return fail(
                "bad_response",
                answered_model=answered_model,
                content_block_types=block_types(),
                stop_reason=stop_reason,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        parts = [
            block["text"]
            for block in content
            if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)
        ]
        if not parts:
            input_tokens, output_tokens = usage_tokens()
            return fail(
                "no_text",
                answered_model=answered_model,
                content_block_types=block_types(),
                stop_reason=stop_reason,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        input_tokens, output_tokens = usage_tokens()
        return ProviderResult(
            ok=True,
            mode="live",
            requested_model=self.config.model_id,
            answered_model=answered_model,
            text="".join(parts),
            latency_ms=elapsed(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error=None,
            content_block_types=block_types(),
            stop_reason=stop_reason,
        )

    complete = generate
    chat = generate
    __call__ = generate


LiveProvider = MetaProvider

BASETEN_BASE_URL = "https://inference.baseten.co/v1"
BASETEN_DEFAULT_MODEL_ID = "meta-models/muse-spark-open-1026"
DEFAULT_BASETEN_MODEL_ID = BASETEN_DEFAULT_MODEL_ID
BASETEN_MODEL_ID = BASETEN_DEFAULT_MODEL_ID
BASETEN_ALLOWED_MODEL_IDS = frozenset({BASETEN_DEFAULT_MODEL_ID})
ALLOWED_BASETEN_MODEL_IDS = BASETEN_ALLOWED_MODEL_IDS


def _validate_baseten_model_id(model_id):
    if model_id is not None and model_id not in BASETEN_ALLOWED_MODEL_IDS:
        raise ValueError(
            f"disallowed Baseten model id: {model_id!r}; "
            f"allowed model ids: {sorted(BASETEN_ALLOWED_MODEL_IDS)}"
        )
    return model_id


@dataclass(frozen=True)
class BasetenConfig:
    base_url: str | None = BASETEN_BASE_URL
    provider_url: str | None = None
    model_id: str | None = BASETEN_DEFAULT_MODEL_ID
    api_key: str | None = field(default=None, repr=False)
    enabled: bool = False
    timeout_s: float = DEFAULT_TIMEOUT_S
    max_tokens: int = DEFAULT_MAX_TOKENS

    def __post_init__(self):
        _validate_baseten_model_id(self.model_id)
        if self.provider_url and not self.base_url:
            object.__setattr__(self, "base_url", self.provider_url)
        elif self.provider_url:
            object.__setattr__(self, "base_url", self.provider_url)
        if self.base_url:
            object.__setattr__(self, "provider_url", self.base_url)

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
        return bool(self.base_url and self.model_id and self.api_key)

    def is_configured(self):
        return self.configured

    def missing_settings(self):
        missing = []
        if not self.model_id:
            missing.append("ARIA_HOME_BASETEN_MODEL_ID")
        if not self.api_key:
            missing.append("BASETEN_API_KEY")
        if not self.enabled:
            missing.append("ARIA_HOME_BASETEN_ENABLED")
        return missing

    @classmethod
    def from_env(cls, env=None):
        source = os.environ if env is None else env
        if isinstance(source, cls):
            return source
        get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
        if not hasattr(source, "get") and not isinstance(source, dict):
            return cls(
                base_url=getattr(source, "base_url", None) or getattr(source, "provider_url", None) or BASETEN_BASE_URL,
                model_id=getattr(source, "model_id", None) or getattr(source, "model", None) or BASETEN_DEFAULT_MODEL_ID,
                api_key=getattr(source, "api_key", None),
                enabled=getattr(source, "enabled", False) in (True, "1", 1),
                timeout_s=float(getattr(source, "timeout_s", None) or getattr(source, "timeout", None) or DEFAULT_TIMEOUT_S),
                max_tokens=int(getattr(source, "max_tokens", None) or getattr(source, "max_output_tokens", None) or DEFAULT_MAX_TOKENS),
            )
        base_url = get("ARIA_HOME_BASETEN_BASE_URL") or get("base_url") or get("provider_url") or BASETEN_BASE_URL
        model_id = get("ARIA_HOME_BASETEN_MODEL_ID") or get("model_id") or get("model") or BASETEN_DEFAULT_MODEL_ID
        api_key = get("BASETEN_API_KEY") or get("api_key")
        raw_enabled = get("ARIA_HOME_BASETEN_ENABLED", get("enabled", False))
        enabled = raw_enabled == "1" or raw_enabled is True or raw_enabled == 1
        timeout_raw = get("timeout_s") or get("timeout") or DEFAULT_TIMEOUT_S
        max_raw = get("max_tokens") or get("max_output_tokens") or get("maxTokens") or DEFAULT_MAX_TOKENS
        if isinstance(base_url, str):
            base_url = base_url.strip() or BASETEN_BASE_URL
        if isinstance(model_id, str):
            model_id = model_id.strip() or None
        if isinstance(api_key, str):
            api_key = api_key.strip() or None
        return cls(
            base_url=base_url,
            model_id=model_id,
            api_key=api_key,
            enabled=enabled,
            timeout_s=float(timeout_raw),
            max_tokens=int(max_raw),
        )


BasetenProviderConfig = BasetenConfig


def _coerce_baseten_config(config=None, env=None):
    if isinstance(config, BasetenConfig):
        return config
    if config is None:
        return BasetenConfig.from_env(env)
    if isinstance(config, dict):
        has_env_keys = any(
            k in config
            for k in ("BASETEN_API_KEY", "ARIA_HOME_BASETEN_MODEL_ID", "ARIA_HOME_BASETEN_ENABLED", "ARIA_HOME_BASETEN_BASE_URL")
        )
        if has_env_keys:
            return BasetenConfig.from_env(config)
        return BasetenConfig(
            base_url=config.get("base_url") or config.get("provider_url") or config.get("url") or BASETEN_BASE_URL,
            model_id=config.get("model_id") or config.get("model") or config.get("requested_model") or BASETEN_DEFAULT_MODEL_ID,
            api_key=config.get("api_key"),
            enabled=config.get("enabled", False) in (True, "1", 1),
            timeout_s=float(config.get("timeout_s") or config.get("timeout") or DEFAULT_TIMEOUT_S),
            max_tokens=int(config.get("max_tokens") or config.get("max_output_tokens") or DEFAULT_MAX_TOKENS),
        )
    return BasetenConfig.from_env(config)


def build_baseten_request(config, messages):
    base = (config.base_url or config.provider_url or BASETEN_BASE_URL).rstrip("/")
    return {
        "url": f"{base}/chat/completions",
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


class BasetenProvider:
    mode = "live"

    def __init__(self, config=None, transport=None, *, timeout=None, timeout_s=None, max_tokens=None, max_output_tokens=None, env=None, api_key=None, model_id=None, enabled=None, base_url=None):
        self.config = _coerce_baseten_config(config, env=env)
        overrides = {}
        if api_key is not None:
            overrides["api_key"] = api_key
        if model_id is not None:
            overrides["model_id"] = model_id
        if enabled is not None:
            overrides["enabled"] = enabled in (True, "1", 1)
        if base_url is not None:
            overrides["base_url"] = base_url
        if overrides:
            from dataclasses import replace as _replace

            self.config = _replace(self.config, **overrides)
        _validate_baseten_model_id(self.config.model_id)
        self.transport = transport
        resolved_timeout = timeout if timeout is not None else timeout_s
        self.timeout_s = float(resolved_timeout) if resolved_timeout is not None else float(self.config.timeout_s)
        resolved_max = max_tokens if max_tokens is not None else max_output_tokens
        self.max_tokens = int(resolved_max) if resolved_max is not None else int(self.config.max_tokens)
        if resolved_max is not None:
            object.__setattr__(self.config, "max_tokens", self.max_tokens)

    @property
    def model_id(self):
        return self.config.model_id

    @property
    def requested_model(self):
        return self.config.model_id

    def generate(self, prompt=None, *, messages=None, max_tokens=None):
        start = time.perf_counter()

        def elapsed():
            return (time.perf_counter() - start) * 1000.0

        def fail(category, answered_model=None, content_block_types=None, stop_reason=None, input_tokens=None, output_tokens=None):
            return ProviderResult(
                ok=False,
                mode="live",
                requested_model=self.config.model_id,
                answered_model=answered_model,
                text=None,
                latency_ms=elapsed(),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                error=category,
                content_block_types=content_block_types,
                stop_reason=stop_reason,
            )

        if not self.config.enabled:
            return fail("disabled")
        if not self.config.api_key:
            return fail("not_configured")
        if not self.config.model_id:
            return fail("not_configured")
        _validate_baseten_model_id(self.config.model_id)

        effective_max = int(max_tokens) if max_tokens is not None else int(self.max_tokens)
        from dataclasses import replace as _replace

        effective_config = _replace(self.config, max_tokens=effective_max)
        request = build_baseten_request(effective_config, _normalize_messages(prompt, messages))
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

        def usage_tokens():
            usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
            raw_in = usage.get("prompt_tokens", usage.get("input_tokens"))
            raw_out = usage.get("completion_tokens", usage.get("output_tokens"))
            return (
                raw_in if isinstance(raw_in, int) else None,
                raw_out if isinstance(raw_out, int) else None,
            )

        answered_model = body.get("model")
        if not isinstance(answered_model, str) or not answered_model:
            return fail("bad_response")
        choices = body.get("choices")
        if not isinstance(choices, list) or len(choices) == 0:
            input_tokens, output_tokens = usage_tokens()
            return fail("bad_response", answered_model=answered_model, input_tokens=input_tokens, output_tokens=output_tokens)
        choice = choices[0] if isinstance(choices[0], dict) else {}
        raw_finish = choice.get("finish_reason") or choice.get("stop_reason")
        stop_reason = raw_finish if isinstance(raw_finish, str) else None
        if answered_model != self.config.model_id:
            input_tokens, output_tokens = usage_tokens()
            return fail("model_mismatch", answered_model=answered_model, stop_reason=stop_reason, input_tokens=input_tokens, output_tokens=output_tokens)

        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        reasoning = None
        for key in ("reasoning_content", "reasoning", "reasoning_text"):
            if isinstance(message.get(key), str) and message.get(key):
                reasoning = message[key]
                break
        if reasoning is None and isinstance(choice.get("reasoning_content"), str):
            reasoning = choice["reasoning_content"]
        if reasoning is None and isinstance(choice.get("reasoning"), str):
            reasoning = choice["reasoning"]

        content = message.get("content")
        text = None
        block_types = []
        if reasoning:
            block_types.append("reasoning")
        if isinstance(content, str):
            text = content
            if content.strip():
                block_types.append("text")
        elif isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict):
                    btype = block.get("type")
                    if btype in ("reasoning", "thinking", "reasoning_content"):
                        if "reasoning" not in block_types:
                            block_types.append("reasoning")
                        continue
                    if isinstance(block.get("text"), str):
                        parts.append(block["text"])
                    elif isinstance(block.get("content"), str) and btype in ("text", "output_text", None):
                        parts.append(block["content"])
            text = "".join(parts) if parts else None
            if text and text.strip():
                block_types.append("text")
        elif isinstance(choice.get("text"), str):
            text = choice["text"]
            if text.strip():
                block_types.append("text")

        input_tokens, output_tokens = usage_tokens()
        if text is None or not text.strip():
            return fail(
                "no_text",
                answered_model=answered_model,
                content_block_types=block_types or None,
                stop_reason=stop_reason,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        return ProviderResult(
            ok=True,
            mode="live",
            requested_model=self.config.model_id,
            answered_model=answered_model,
            text=text,
            latency_ms=elapsed(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error=None,
            content_block_types=block_types or None,
            stop_reason=stop_reason,
        )

    complete = generate
    chat = generate
    __call__ = generate


_SECRET_KEY_PARTS = ("api_key", "apikey", "authorization", "secret", "password", "credential", "auth_token", "access_token")


def _endpoint_identity(raw_url):
    if not raw_url:
        return None
    from urllib.parse import urlparse

    text = str(raw_url).strip()
    parsed = urlparse(text if "://" in text else f"//{text}")
    host = (parsed.hostname or "").lower()
    if parsed.port:
        host = f"{host}:{parsed.port}"
    path = parsed.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")
    return {"host": host, "path": path}


def _sanitize_generation(value):
    if not isinstance(value, dict):
        return {}
    out = {}
    for key in sorted(value):
        lowered = str(key).lower()
        if any(part in lowered for part in _SECRET_KEY_PARTS):
            continue
        item = value[key]
        if isinstance(item, (str, int, float, bool)) or item is None:
            out[str(key)] = item
    return out


def normalized_provider_identity(provider=None):
    if isinstance(provider, dict) and any(k in provider for k in ("mode", "provider", "model_id", "endpoint", "generation")) and not any(k in provider for k in ("provider_url", "base_url", "url", "api_key")):
        endpoint = provider.get("endpoint")
        if isinstance(endpoint, str):
            endpoint = _endpoint_identity(endpoint)
        elif isinstance(endpoint, dict):
            endpoint = {"host": str(endpoint.get("host") or "").lower(), "path": str(endpoint.get("path") or "/")}
        return {
            "mode": str(provider.get("mode") or "unspecified").lower(),
            "provider": str(provider.get("provider") or provider.get("provider_id") or "unspecified"),
            "model_id": provider.get("model_id"),
            "endpoint": endpoint,
            "generation": _sanitize_generation(provider.get("generation") or {}),
        }
    if provider is None:
        return {"mode": "unspecified", "provider": "unspecified", "model_id": None, "endpoint": None, "generation": {}}
    config = getattr(provider, "config", None)
    if config is None and isinstance(provider, (ProviderConfig, BasetenConfig)):
        config = provider
    def _attr(*names):
        for obj in (provider, config):
            if obj is None:
                continue
            for name in names:
                value = getattr(obj, name, None) if not isinstance(obj, dict) else obj.get(name)
                if value is not None:
                    return value
        return None

    mode = _attr("mode")
    if mode is None:
        mode = "live" if _attr("enabled") else "mock"
    model_id = _attr("model_id", "requested_model", "model")
    raw_url = _attr("provider_url", "base_url", "url", "endpoint")
    generation = {}
    explicit = _attr("generation", "generation_settings")
    if isinstance(explicit, dict):
        generation.update(_sanitize_generation(explicit))
    max_tokens = _attr("max_tokens", "max_output_tokens")
    if max_tokens is not None:
        generation["max_tokens"] = int(max_tokens)
    provider_name = _attr("provider_name", "provider_id", "provider_identity") or type(provider).__name__
    return {
        "mode": str(mode).lower(),
        "provider": str(provider_name),
        "model_id": str(model_id) if model_id is not None else None,
        "endpoint": _endpoint_identity(raw_url),
        "generation": generation,
    }


def get_provider(env=None):
    config = _coerce_config(env) if not isinstance(env, ProviderConfig) else env
    if isinstance(env, ProviderConfig):
        config = env
    elif env is not None and not isinstance(env, dict):
        config = _coerce_config(env)
    _validate_model_id(config.model_id)
    if not config.enabled:
        return MockProvider(model_id=config.model_id or DEFAULT_MODEL_ID)
    return MetaProvider(config)
