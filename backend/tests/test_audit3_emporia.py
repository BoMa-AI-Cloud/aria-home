import json
import socket
from datetime import datetime
from pathlib import Path

from aria_home import emporia
from aria_home.app import create_app
from aria_home.investigator import build_evidence_pack
from aria_home.scenario import load_scenario
from aria_home.verification import verify_recovery
from aria_home.outcomes import follow_up_for
from pyemvue.device import VueDeviceChannelUsage, VueUsageDevice

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"

EMAIL = "owner@example.com"
PASSWORD = "test-emporia-password"


def _usage_device(gid, entries, timestamp=None):
    device = VueUsageDevice(gid=gid)
    device.device_gid = gid
    device.timestamp = timestamp
    channels = {}
    for channel_num, name, usage in entries:
        channel = VueDeviceChannelUsage()
        channel.channel_num = channel_num
        channel.name = name
        channel.device_gid = gid
        channel.usage = usage
        channels[channel_num] = channel
    device.channels = channels
    return device


class FakeVue:
    def __init__(self, calls, usage=None, error=None, seen=None):
        self.calls = calls
        self.usage = usage
        self.error = error
        self.seen = seen if seen is not None else {}

    def login(self, username=None, password=None):
        self.calls.append("login")
        assert username == EMAIL and password == PASSWORD
        if self.error == "login":
            raise RuntimeError("bad credentials (test)")
        return "fake-token"

    def get_devices(self):
        self.calls.append("get_devices")
        if self.error == "devices":
            raise RuntimeError("devices unavailable (test)")
        return [{"device_gid": 111}, {"device_gid": 222}]

    def get_device_list_usage(self, deviceGids, instant=None, scale="1S", unit="KilowattHours"):
        self.calls.append("get_device_list_usage")
        self.seen.update({"gids": deviceGids, "instant": instant, "scale": scale, "unit": unit})
        if self.error == "usage":
            raise RuntimeError("usage unavailable (test)")
        if self.usage is not None:
            return self.usage
        return {
            111: _usage_device(111, [("1", "mains", 0.000234), ("2", "furnace", 0.0)]),
            222: _usage_device(222, [("1", "water_heater", 0.0000035)]),
        }


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    return create_app().test_client()


def _emporia_env(monkeypatch, **overrides):
    for name in ("EMPORIA_EMAIL", "EMPORIA_PASSWORD", "ARIA_HOME_EMPORIA_LIVE"):
        monkeypatch.delenv(name, raising=False)
    env = {"EMPORIA_EMAIL": EMAIL, "EMPORIA_PASSWORD": PASSWORD, "ARIA_HOME_EMPORIA_LIVE": "1"}
    env.update(overrides)
    for name, value in env.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)


def _factory(monkeypatch, calls, **kwargs):
    seen = kwargs.pop("seen", None)
    fake = FakeVue(calls, seen=seen, **kwargs)
    monkeypatch.setattr(emporia, "_client_factory", lambda: fake)
    return fake


def test_default_off_reports_not_configured(tmp_path, monkeypatch):
    for name in ("EMPORIA_EMAIL", "EMPORIA_PASSWORD", "ARIA_HOME_EMPORIA_LIVE"):
        monkeypatch.delenv(name, raising=False)

    def blocked(*args, **kwargs):
        raise AssertionError("network socket use attempted")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    emporia.clear_live_power_cache()
    try:
        client = _client(tmp_path, monkeypatch)
        resp = client.get("/api/live-power")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "not_configured"
        assert body["circuits"] == []
        assert body["fetched_at"] is None
        assert body["source"] == "live-read-only (owner's home)"
    finally:
        emporia.clear_live_power_cache()


def test_each_missing_env_var_stays_not_configured(tmp_path, monkeypatch):
    for name in ("EMPORIA_EMAIL", "EMPORIA_PASSWORD", "ARIA_HOME_EMPORIA_LIVE"):
        _emporia_env(monkeypatch, **{name: None})
        emporia.clear_live_power_cache()
        try:
            client = _client(tmp_path, monkeypatch)
            assert client.get("/api/live-power").get_json()["status"] == "not_configured", name
        finally:
            emporia.clear_live_power_cache()


def test_ok_returns_watts_and_caches_sixty_seconds(tmp_path, monkeypatch):
    _emporia_env(monkeypatch)
    calls = []
    _factory(monkeypatch, calls)
    emporia.clear_live_power_cache()
    try:
        client = _client(tmp_path, monkeypatch)
        first = client.get("/api/live-power").get_json()
        assert first["status"] == "ok"
        assert first["source"] == "live-read-only (owner's home)"
        assert first["fetched_at"]
        assert first["circuits"] == [
            {"circuit": "111/furnace", "watts": 0.0},
            {"circuit": "111/mains", "watts": 842.4},
            {"circuit": "222/water_heater", "watts": 12.6},
        ]
        assert first["cached"] is False
        assert calls == ["login", "get_devices", "get_device_list_usage"]
        second = client.get("/api/live-power").get_json()
        assert second["status"] == "ok"
        assert second["cached"] is True
        assert second["fetched_at"] == first["fetched_at"]
        assert calls == ["login", "get_devices", "get_device_list_usage"]
    finally:
        emporia.clear_live_power_cache()


def test_stale_cache_refetches(tmp_path, monkeypatch):
    _emporia_env(monkeypatch)
    calls = []
    _factory(monkeypatch, calls)
    emporia.clear_live_power_cache()
    try:
        client = _client(tmp_path, monkeypatch)
        assert client.get("/api/live-power").get_json()["status"] == "ok"
        emporia._CACHE["fetched_at"] -= (emporia.LIVE_POWER_CACHE_S + 1)
        assert client.get("/api/live-power").get_json()["cached"] is False
        assert calls.count("login") == 2
    finally:
        emporia.clear_live_power_cache()


def test_failure_is_unavailable_never_500_and_no_secrets(tmp_path, monkeypatch):
    for error in ("login", "devices", "usage"):
        _emporia_env(monkeypatch)
        calls = []
        _factory(monkeypatch, calls, error=error)
        emporia.clear_live_power_cache()
        try:
            client = _client(tmp_path, monkeypatch)
            resp = client.get("/api/live-power")
            assert resp.status_code == 200, error
            body = resp.get_json()
            assert body["status"] == "unavailable", error
            assert body["circuits"] == []
            text = resp.get_data(as_text=True)
            assert EMAIL not in text and PASSWORD not in text, error
        finally:
            emporia.clear_live_power_cache()


def test_only_read_methods_called(tmp_path, monkeypatch):
    _emporia_env(monkeypatch)
    calls = []
    _factory(monkeypatch, calls)
    emporia.clear_live_power_cache()
    try:
        client = _client(tmp_path, monkeypatch)
        assert client.get("/api/live-power").get_json()["status"] == "ok"
        assert set(calls) <= {"login", "get_devices", "get_device_list_usage"}
    finally:
        emporia.clear_live_power_cache()


def test_usage_called_with_explicit_instant_scale_unit(tmp_path, monkeypatch):
    _emporia_env(monkeypatch)
    calls = []
    seen = {}
    _factory(monkeypatch, calls, seen=seen)
    emporia.clear_live_power_cache()
    try:
        client = _client(tmp_path, monkeypatch)
        assert client.get("/api/live-power").get_json()["status"] == "ok"
        assert seen["gids"] == [111, 222]
        assert seen["instant"] is not None and seen["instant"].tzinfo is not None and seen["instant"].utcoffset() is not None
        assert seen["scale"] == "1S"
        assert seen["unit"] == "KilowattHours"
    finally:
        emporia.clear_live_power_cache()


def test_live_panel_changes_nothing_about_readiness_or_verification(tmp_path, monkeypatch):
    at = "2026-01-16T18:51:00-05:00"
    scenario = load_scenario(SCENARIOS / "demo_video_v1")
    moment = datetime.fromisoformat(at)

    def snapshot(client):
        metrics = client.get(f"/api/metrics?scenario=demo_video_v1&at={at}").get_json()
        investigation = client.get(f"/api/investigation?scenario=demo_video_v1&at={at}").get_json()
        pack = build_evidence_pack(scenario, moment)
        follow_up = follow_up_for(scenario, "probe-noninterference", datetime.fromisoformat("2026-01-16T16:31:00-05:00"))
        stage = verify_recovery(scenario, follow_up, moment)["stage"]
        return metrics["computed_readiness"], investigation["computed_readiness"], stage, pack

    client = _client(tmp_path, monkeypatch)
    off = snapshot(client)
    _emporia_env(monkeypatch)
    calls = []
    _factory(monkeypatch, calls)
    emporia.clear_live_power_cache()
    try:
        assert client.get("/api/live-power").get_json()["status"] == "ok"
        on = snapshot(client)
    finally:
        emporia.clear_live_power_cache()
    assert on[:3] == off[:3]
    text = json.dumps(on[3])
    assert "emporia" not in text.lower()
    assert "live-read-only" not in text
