"""Optional Emporia Vue read-only live panel.

Off by default. Live data is fetched only when EMPORIA_EMAIL and
EMPORIA_PASSWORD are both set plus the explicit opt-in
ARIA_HOME_EMPORIA_LIVE=1. Otherwise GET /api/live-power reports
not_configured and the frontend hides the panel, so the judge demo is
unchanged.

Only read methods of the installed pyemvue package are ever called
(login, device list, current usage). No method that changes a device or
outlet is called anywhere in this repository; pyemvue itself offers no
control calls, and this module never imports or references any.

Live watts are display only. They are NOT evidence for readiness,
warming or verification and never enter the evidence pack (watts are
not heat). Responses carry per-circuit watts, the source label, and the
fetch time. Credentials only come from environment variables and never
appear in responses, stored rows, logs or errors.
"""

import os
import time
from datetime import datetime, timezone

LIVE_POWER_SOURCE = "live-read-only (owner's home)"
LIVE_POWER_CACHE_S = 60

_CACHE = {"fetched_at": None, "payload": None}

_client_factory = None


def emporia_config_from_env(env=None):
    source = os.environ if env is None else env
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    email = (get("EMPORIA_EMAIL") or "").strip()
    password = get("EMPORIA_PASSWORD") or ""
    live = (get("ARIA_HOME_EMPORIA_LIVE") or "").strip() == "1"
    configured = bool(live and email and password)
    return {"email": email, "password": password, "live": live, "configured": configured}


def clear_live_power_cache():
    _CACHE["fetched_at"] = None
    _CACHE["payload"] = None


def _scrub(text, config):
    cleaned = str(text)
    for secret in (config.get("email"), config.get("password")):
        if secret:
            cleaned = cleaned.replace(secret, "[redacted]")
    return cleaned


def _channel_watts(channel):
    get = channel.get if isinstance(channel, dict) else lambda k, d=None: getattr(channel, k, d)
    name = get("name", get("channelName", "circuit"))
    for key in ("usage", "watts", "wattage", "power"):
        value = get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return str(name), float(value)
    return str(name), None


def _extract_circuits(usage_by_gid):
    circuits = []
    items = usage_by_gid.items() if isinstance(usage_by_gid, dict) else []
    for gid, usage in items:
        get = usage.get if isinstance(usage, dict) else lambda k, d=None: getattr(usage, k, d)
        channels = get("channels") or {}
        entries = channels.items() if isinstance(channels, dict) else enumerate(channels or [])
        for _, channel in entries:
            name, watts = _channel_watts(channel)
            if watts is None:
                continue
            circuits.append({"circuit": f"{gid}/{name}", "watts": round(watts, 1)})
    circuits.sort(key=lambda c: c["circuit"])
    return circuits


def _default_client_factory():
    from pyemvue import PyEmVue

    return PyEmVue()


def _read_fresh(config, client_factory):
    factory = client_factory or _client_factory or _default_client_factory
    try:
        client = factory()
    except Exception as exc:
        return {"status": "unavailable", "error": _scrub(f"client_error: {exc}", config)[:200]}
    try:
        client.login(username=config["email"], password=config["password"])
        devices = client.get_devices()
    except Exception as exc:
        return {"status": "unavailable", "error": _scrub(f"login_error: {exc}", config)[:200]}
    try:
        gids = []
        for device in devices or []:
            get = device.get if isinstance(device, dict) else lambda k, d=None: getattr(device, k, d)
            gid = get("device_gid", get("deviceGid"))
            if gid:
                gids.append(gid)
        usage = client.get_device_list_usage(gids) if gids else {}
        response = usage.get("devices") if isinstance(usage, dict) else getattr(usage, "devices", usage)
        circuits = _extract_circuits(response or {})
    except Exception as exc:
        return {"status": "unavailable", "error": _scrub(f"usage_error: {exc}", config)[:200]}
    return {"status": "ok", "circuits": circuits}


def read_live_power(*, env=None, client_factory=None):
    """Return the cached-or-fresh live-power payload. Never raises."""
    config = emporia_config_from_env(env)
    if not config["configured"]:
        return {"status": "not_configured", "source": LIVE_POWER_SOURCE, "fetched_at": None, "circuits": []}
    now = time.time()
    if _CACHE["fetched_at"] is not None and now - _CACHE["fetched_at"] < LIVE_POWER_CACHE_S and _CACHE["payload"]:
        payload = dict(_CACHE["payload"])
        payload["cached"] = True
        return payload
    try:
        result = _read_fresh(config, client_factory)
    except Exception as exc:
        result = {"status": "unavailable", "error": _scrub(f"error: {exc}", config)[:200]}
    if result.get("status") != "ok":
        return {"status": "unavailable", "source": LIVE_POWER_SOURCE, "fetched_at": None, "circuits": [], "error": result.get("error", "unavailable")}
    payload = {
        "status": "ok",
        "source": LIVE_POWER_SOURCE,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "circuits": result["circuits"],
        "cached": False,
    }
    _CACHE["fetched_at"] = now
    _CACHE["payload"] = dict(payload)
    return payload
