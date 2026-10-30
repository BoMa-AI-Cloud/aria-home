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

SDK contract (installed PyEmVue 0.18.9, ``pyemvue.device``): usage is read
with ``get_device_list_usage(deviceGids, instant, scale='1S',
unit='KilowattHours')``, which returns ``dict[int, VueUsageDevice]`` keyed
by integer device gid. Each device carries ``channels: dict[str,
VueDeviceChannelUsage]`` keyed by channel number; each channel's ``usage``
is ENERGY in the requested unit over the scale interval (kilowatt-hours
over one second here), never watts. Average power is derived as
``kWh * 3600000 / interval_s`` (0.001 kWh over 1 s = 3600 W). Unknown,
malformed, non-finite or unsupported values are skipped, never relabelled
as watts.

Live watts are display only. They are NOT evidence for readiness,
warming or verification and never enter the evidence pack (watts are
not heat). Responses carry per-circuit watts, the source label, and the
fetch time. Credentials only come from environment variables and never
appear in responses, stored rows, logs or errors.
"""

import math
import os
import time
from datetime import datetime, timezone

LIVE_POWER_SOURCE = "live-read-only (owner's home)"
LIVE_POWER_CACHE_S = 60
REQUEST_SCALE = "1S"
REQUEST_UNIT = "KilowattHours"
SCALE_INTERVAL_S = {"1S": 1, "1MIN": 60, "15MIN": 900, "1H": 3600, "1D": 86400, "1W": 604800}
KWH_TO_JOULES = 3_600_000

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


def _get(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _kwh_to_watts(usage_kwh, interval_s):
    """Convert interval energy (kWh) to average power (W); None if unusable."""
    if isinstance(usage_kwh, bool):
        return None
    if not isinstance(usage_kwh, (int, float)):
        return None
    if not math.isfinite(usage_kwh):
        return None
    return usage_kwh * KWH_TO_JOULES / interval_s


def _channel_circuits(gid_label, usage):
    circuits = []
    channels = _get(usage, "channels") or {}
    items = channels.items() if isinstance(channels, dict) else []
    for _, channel in items:
        if channel is None:
            continue
        name = _get(channel, "name", _get(channel, "channelName", "circuit"))
        watts = _kwh_to_watts(_get(channel, "usage"), SCALE_INTERVAL_S[REQUEST_SCALE])
        if watts is None:
            continue
        circuits.append({"circuit": f"{gid_label}/{name}", "watts": round(watts, 1)})
    return circuits


def _extract_circuits(usage_by_gid):
    circuits = []
    items = usage_by_gid.items() if isinstance(usage_by_gid, dict) else []
    for key, usage in items:
        if usage is None:
            continue
        gid = _get(usage, "device_gid", _get(usage, "deviceGid", key))
        circuits.extend(_channel_circuits(gid, usage))
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
            gid = _get(device, "device_gid", _get(device, "deviceGid"))
            if gid is None or gid == "":
                continue
            gids.append(gid)
        instant = datetime.now(timezone.utc)
        usage = client.get_device_list_usage(gids, instant, scale=REQUEST_SCALE, unit=REQUEST_UNIT) if gids else {}
        circuits = _extract_circuits(usage or {})
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
