"""Audit 4 Group B: API and optional-integration repairs (findings 5-9)."""
import json
import math
import socket
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

from pyemvue.device import VueDeviceChannelUsage, VueUsageDevice

from aria_home import emporia, whatsapp
from aria_home.app import create_app
from aria_home.investigator import build_evidence_pack
from aria_home.notifications import ALLOWLISTS
from aria_home.readiness import compute_readiness
from aria_home.scenario import load_scenario

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
VISUAL_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "visual"

INV_AT = "2026-01-16T16:31:00-05:00"
VALID_ACK_AT = "2026-01-16T16:37:00-05:00"

EMAIL = "owner@example.com"
PASSWORD = "test-emporia-password"

TOKEN = "test-whatsapp-token-abc123"
PHONE_ID = "19876543210"
RECIPIENT = "+15550001111"
LIVE_ENV = {
    "WHATSAPP_TOKEN": TOKEN,
    "WHATSAPP_PHONE_NUMBER_ID": PHONE_ID,
    "WHATSAPP_TEST_RECIPIENT": RECIPIENT,
    "ARIA_HOME_WHATSAPP_LIVE": "1",
}
FOLLOW_AT = "2026-01-16T16:52:00-05:00"


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    return create_app().test_client()


def _manager_notice(client):
    resp = client.post(f"/api/investigations?scenario=demo_video_v1&at={INV_AT}")
    assert resp.status_code == 200
    inv_id = resp.get_json()["investigation_id"]
    rows = client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"]
    notice = next(r for r in rows if r["audience"] == "property_manager" and r["state"] == "simulated_delivered")
    return inv_id, notice


def _refused_notice(client):
    resp = client.post("/api/investigations?scenario=demo_video_v1&at=2026-01-16T09:05:00-05:00")
    assert resp.status_code == 200
    inv_id = resp.get_json()["investigation_id"]
    rows = client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"]
    refused = [r for r in rows if r["state"] != "simulated_delivered"]
    assert refused, rows
    return inv_id, refused[0]


def _ack(client, notification_id, body=None, raw=None, query=""):
    if raw is not None:
        return client.post(
            f"/api/notifications/{notification_id}/ack{query}",
            data=raw,
            content_type="application/json",
        )
    return client.post(f"/api/notifications/{notification_id}/ack{query}", json=body)


# Finding 5: empty/invalid ack timestamps must be 4xx, never 500.


def test_ack_empty_and_whitespace_at_are_400(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, notice = _manager_notice(client)
    for at in ("", "  "):
        resp = _ack(client, notice["id"], body={"actor": "property_manager", "at": at})
        assert resp.status_code == 400, at
        assert "at" in resp.get_json()["error"].lower()


def test_ack_null_number_list_at_are_400(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, notice = _manager_notice(client)
    for at in (None, 5, ["2026-01-16T16:37:00-05:00"], {"at": VALID_ACK_AT}):
        resp = _ack(client, notice["id"], body={"actor": "property_manager", "at": at})
        assert resp.status_code == 400, repr(at)


def test_ack_omitted_at_defaults_to_now(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, notice = _manager_notice(client)
    resp = _ack(client, notice["id"], body={"actor": "property_manager"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ack"]["actor"] == "property_manager"
    assert body["ack"]["acknowledged_at"]


def test_ack_non_object_bodies_are_400(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, notice = _manager_notice(client)
    for raw in ("[1, 2]", '"actor"', "5", "null", "{bad json"):
        resp = _ack(client, notice["id"], raw=raw)
        assert resp.status_code == 400, raw


def test_ack_naive_malformed_and_early_at_are_400(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, notice = _manager_notice(client)
    for at in ("2026-01-16T16:37:00", "not-a-date", "2026-01-16T16:00:00-05:00"):
        resp = _ack(client, notice["id"], body={"actor": "property_manager", "at": at})
        assert resp.status_code == 400, at


def test_ack_unknown_actor_refused_notice_and_unknown_id(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, notice = _manager_notice(client)
    resp = _ack(client, notice["id"], body={"actor": "intruder", "at": VALID_ACK_AT})
    assert resp.status_code == 403
    _, refused = _refused_notice(client)
    resp = _ack(client, refused["id"], body={"actor": refused["audience"], "at": VALID_ACK_AT})
    assert resp.status_code == 409
    resp = _ack(client, "notif-does-not-exist", body={"actor": "property_manager", "at": VALID_ACK_AT})
    assert resp.status_code == 404


def test_ack_valid_and_repeated_valid_ack(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, notice = _manager_notice(client)
    resp = _ack(client, notice["id"], body={"actor": "property_manager", "at": VALID_ACK_AT})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["message"] == "acknowledged, not resolved"
    assert body["ack"]["acknowledged_at"].startswith("2026-01-16T16:37")
    resp = _ack(client, notice["id"], body={"actor": "property_manager", "at": VALID_ACK_AT})
    assert resp.status_code == 200
    assert len(resp.get_json()["acks"]) == 1
    rows = client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"]
    acked = next(r for r in rows if r["id"] == notice["id"])
    assert acked["state"] == "simulated_delivered"
    assert len(acked["acks"]) == 1
    early = client.get(f"/api/notifications?investigation_id={inv_id}&at=2026-01-16T16:35:00-05:00").get_json()["notifications"]
    assert next(r for r in early if r["id"] == notice["id"])["acks"] == []


def test_ack_no_malformed_input_gives_500(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, notice = _manager_notice(client)
    bodies = [
        {"actor": "property_manager", "at": ""},
        {"actor": "property_manager", "at": "  "},
        {"actor": "property_manager", "at": None},
        {"actor": "property_manager", "at": 5},
        {"actor": "property_manager", "at": ["x"]},
        {"actor": "property_manager", "at": "2026-01-16T16:37:00"},
        {"actor": "property_manager", "at": "bogus"},
        {"actor": "", "at": ""},
        {"at": ""},
        {},
    ]
    for body in bodies:
        assert _ack(client, notice["id"], body=body).status_code != 500, body
    for raw in ("[1]", '"x"', "null", "{oops"):
        assert _ack(client, notice["id"], raw=raw).status_code != 500, raw
    assert _ack(client, notice["id"], body={"actor": "property_manager"}, query="?at=").status_code == 400


def test_ack_query_param_at_and_alias(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, notice = _manager_notice(client)
    resp = _ack(client, notice["id"], body={"actor": "property_manager"}, query=f"?at={VALID_ACK_AT}")
    assert resp.status_code == 200
    _, notice2 = _manager_notice(client)
    resp = _ack(client, notice2["id"], body={"actor": "property_manager", "acknowledged_at": VALID_ACK_AT})
    assert resp.status_code == 200


# Finding 6: Emporia adapter matches the PyEmVue 0.18.9 SDK.


def _sdk_device(gid, entries):
    device = VueUsageDevice(gid=gid)
    device.device_gid = gid
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


class _SdkFakeVue:
    def __init__(self, calls, devices=None, usage=None, error=None, seen=None):
        self.calls = calls
        self.devices = devices
        self.usage = usage
        self.error = error
        self.seen = seen if seen is not None else {}

    def login(self, username=None, password=None):
        self.calls.append("login")
        assert (username, password) == (EMAIL, PASSWORD)
        if self.error == "login":
            raise RuntimeError("bad credentials (test)")
        return "fake-token"

    def get_devices(self):
        self.calls.append("get_devices")
        if self.error == "devices":
            raise RuntimeError("devices unavailable (test)")
        if self.devices is not None:
            return self.devices
        device = VueUsageDevice(gid=777)
        device.device_gid = 777
        return [device]

    def get_device_list_usage(self, deviceGids, instant=None, scale="1S", unit="KilowattHours"):
        self.calls.append("get_device_list_usage")
        self.seen.update({"gids": deviceGids, "instant": instant, "scale": scale, "unit": unit})
        if self.error == "usage":
            raise RuntimeError("usage unavailable (test)")
        if self.usage is not None:
            return self.usage
        return {777: _sdk_device(777, [("1", "mains", 0.001)])}


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


def _emporia_client(monkeypatch, calls, **kwargs):
    seen = kwargs.pop("seen", None)
    fake = _SdkFakeVue(calls, seen=seen, **kwargs)
    monkeypatch.setattr(emporia, "_client_factory", lambda: fake)
    return fake


def _live_power(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    return create_app().test_client()


def test_emporia_3600w_energy_conversion(tmp_path, monkeypatch):
    _emporia_env(monkeypatch)
    calls = []
    seen = {}
    _emporia_client(monkeypatch, calls, seen=seen)
    emporia.clear_live_power_cache()
    try:
        body = _live_power(tmp_path, monkeypatch).get("/api/live-power").get_json()
        assert body["status"] == "ok"
        assert body["circuits"] == [{"circuit": "777/mains", "watts": 3600.0}]
        assert seen["scale"] == "1S" and seen["unit"] == "KilowattHours"
        instant = seen["instant"]
        assert instant.tzinfo is not None and instant.utcoffset() is not None
    finally:
        emporia.clear_live_power_cache()


def test_emporia_empty_devices_and_missing_channels(tmp_path, monkeypatch):
    _emporia_env(monkeypatch)
    calls = []
    _emporia_client(monkeypatch, calls, devices=[], usage={"unexpected": "call"})
    emporia.clear_live_power_cache()
    try:
        body = _live_power(tmp_path, monkeypatch).get("/api/live-power").get_json()
        assert body["status"] == "ok"
        assert body["circuits"] == []
        assert "get_device_list_usage" not in calls
    finally:
        emporia.clear_live_power_cache()
    calls = []
    _emporia_client(monkeypatch, calls, usage={777: _sdk_device(777, [])})
    emporia.clear_live_power_cache()
    try:
        body = _live_power(tmp_path, monkeypatch).get("/api/live-power").get_json()
        assert body["status"] == "ok"
        assert body["circuits"] == []
        assert "get_device_list_usage" in calls
    finally:
        emporia.clear_live_power_cache()


def test_emporia_malformed_values_never_become_watts(tmp_path, monkeypatch):
    _emporia_env(monkeypatch)
    calls = []
    usage = {
        777: _sdk_device(
            777,
            [
                ("1", "ok", 0.00025),
                ("2", "none", None),
                ("3", "text", "lots"),
                ("4", "bool", True),
                ("5", "nan", math.nan),
                ("6", "inf", math.inf),
            ],
        )
    }
    _emporia_client(monkeypatch, calls, usage=usage)
    emporia.clear_live_power_cache()
    try:
        body = _live_power(tmp_path, monkeypatch).get("/api/live-power").get_json()
        assert body["status"] == "ok"
        assert body["circuits"] == [{"circuit": "777/ok", "watts": 900.0}]
    finally:
        emporia.clear_live_power_cache()


def test_emporia_sdk_exceptions_are_unavailable(tmp_path, monkeypatch):
    for error in ("login", "devices", "usage"):
        _emporia_env(monkeypatch)
        calls = []
        _emporia_client(monkeypatch, calls, error=error)
        emporia.clear_live_power_cache()
        try:
            resp = _live_power(tmp_path, monkeypatch).get("/api/live-power")
            assert resp.status_code == 200, error
            body = resp.get_json()
            assert body["status"] == "unavailable", error
            assert body["circuits"] == []
            text = resp.get_data(as_text=True)
            assert EMAIL not in text and PASSWORD not in text, error
        finally:
            emporia.clear_live_power_cache()


def test_emporia_disabled_mode_makes_no_calls(tmp_path, monkeypatch):
    for name in ("EMPORIA_EMAIL", "EMPORIA_PASSWORD", "ARIA_HOME_EMPORIA_LIVE"):
        monkeypatch.delenv(name, raising=False)

    def blocked(*args, **kwargs):
        raise AssertionError("emporia client must not be constructed when disabled")

    monkeypatch.setattr(emporia, "_client_factory", blocked)
    emporia.clear_live_power_cache()
    try:
        body = _live_power(tmp_path, monkeypatch).get("/api/live-power").get_json()
        assert body["status"] == "not_configured"
        assert body["circuits"] == []
    finally:
        emporia.clear_live_power_cache()


def test_emporia_readiness_unaffected(tmp_path, monkeypatch):
    at = datetime.fromisoformat("2026-01-16T18:51:00-05:00")
    scenario = load_scenario(SCENARIOS / "demo_video_v1")
    _emporia_env(monkeypatch)
    calls = []
    _emporia_client(monkeypatch, calls)
    emporia.clear_live_power_cache()
    try:
        assert _live_power(tmp_path, monkeypatch).get("/api/live-power").get_json()["status"] == "ok"
        pack = build_evidence_pack(scenario, at)
        result = compute_readiness(pack, at)
        text = json.dumps({"pack": pack, "readiness": result})
        assert "live-read-only" not in text
        assert "emporia" not in text.lower()
        assert result["status"] in ("on_track", "at_risk", "cannot_tell", "arrival_passed")
    finally:
        emporia.clear_live_power_cache()


# Finding 7: the app is replay-only; the live opt-in changes nothing.


def _blocked_socket(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("network socket use attempted")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def test_visual_live_env_changes_nothing(tmp_path, monkeypatch):
    _blocked_socket(monkeypatch)
    for name in ("ARIA_HOME_VISUAL_LIVE", "MODEL_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    client = _client(tmp_path, monkeypatch)
    plain = client.get("/api/visual?scenario=visual_water_low_temp_v1&at=2026-01-16T18:00:00-05:00")
    assert plain.status_code == 200
    monkeypatch.setenv("ARIA_HOME_VISUAL_LIVE", "1")
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    opted = client.get("/api/visual?scenario=visual_water_low_temp_v1&at=2026-01-16T18:00:00-05:00")
    assert opted.status_code == 200
    assert opted.get_json() == plain.get_json()
    assert opted.get_json()["visual"]["provider_mode"] == "recorded"
    image = client.get(opted.get_json()["visual"]["image_url"])
    assert image.status_code == 200


def test_visual_replay_provenance_and_as_of(tmp_path, monkeypatch):
    _blocked_socket(monkeypatch)
    client = _client(tmp_path, monkeypatch)
    body = client.get("/api/visual?scenario=visual_water_low_temp_v1&at=2026-01-16T18:00:00-05:00").get_json()
    visual = body["visual"]
    assert visual["image_synthetic"] is True
    assert visual["generator"] == "muse-image-1.0"
    assert visual["model"] == "sam-3.1"
    assert visual["provider_mode"] == "recorded"
    assert visual["caption"].endswith("(recorded)")
    assert visual["observed_at"] and visual["received_at"]
    early = client.get("/api/visual?scenario=visual_water_low_temp_v1&at=2026-01-16T17:00:00-05:00").get_json()
    assert early["visual"] is None


def test_visual_empty_segmentation_stays_conservative(tmp_path, monkeypatch):
    at = datetime.fromisoformat("2026-01-16T18:00:00-05:00")
    for name in ("visual_dry_floor_v1", "visual_frost_missed_v1"):
        scenario = load_scenario(SCENARIOS / name)
        assert scenario.visual["object_count"] == 0
        result = compute_readiness(build_evidence_pack(scenario, at), at)
        assert result["status"] == "at_risk"
        assert "not an all-clear" in " ".join(result["reasons"])


def test_visual_allowlists_exclude_images(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    resp = client.post("/api/investigations?scenario=visual_water_low_temp_v1&at=2026-01-16T18:00:00-05:00")
    assert resp.status_code == 200
    rows = client.get(f"/api/notifications?investigation_id={resp.get_json()['investigation_id']}").get_json()["notifications"]
    assert rows
    for row in rows:
        assert set(row["payload"]) <= ALLOWLISTS[row["audience"]]
        dumped = json.dumps(row["payload"])
        for token in ("webp", "base64", "data:image", "image_url", "mask", "box;x1"):
            assert token not in dumped


# Finding 8: WhatsApp uncertain responses are unknown, never success.


def _live_env(monkeypatch, **overrides):
    for name in whatsapp.REQUIRED_ENV:
        monkeypatch.delenv(name, raising=False)
    env = dict(LIVE_ENV)
    env.update(overrides)
    for name, value in env.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)


def _hvac_notice(client, fake):
    resp = client.post(f"/api/investigations?scenario=demo_video_v1&at={INV_AT}")
    assert resp.status_code == 200
    inv_id = resp.get_json()["investigation_id"]
    resp = client.get(f"/api/follow-ups/{inv_id}?at={FOLLOW_AT}")
    assert resp.status_code == 200
    rows = client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"]
    return inv_id, next(r for r in rows if r["audience"] == "hvac_company" and r["state"] == "simulated_delivered")


class _FakeHttp:
    def __init__(self, status=200, payload=None, error=None):
        self.calls = []
        self.status = status
        self.payload = payload if payload is not None else {"messages": [{"id": "wamid.TEST123"}]}
        self.error = error

    def __call__(self, url, headers, body):
        self.calls.append({"url": url, "headers": headers, "body": body})
        if self.error is not None:
            raise self.error
        return self.status, self.payload


def _attempt_rows(tmp_path):
    conn = sqlite3.connect(tmp_path / "api.db")
    try:
        return conn.execute("SELECT notification_id, state, message_id, attempted_at FROM whatsapp_attempts").fetchall()
    finally:
        conn.close()


def test_whatsapp_200_without_id_is_unknown(tmp_path, monkeypatch):
    _live_env(monkeypatch)
    fake = _FakeHttp(payload={})
    monkeypatch.setattr(whatsapp, "_http_post", fake)
    client = _client(tmp_path, monkeypatch)
    inv_id, hvac = _hvac_notice(client, fake)
    resp = client.post(f"/api/notifications/{hvac['id']}/whatsapp")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["delivery"]["attempted"] is True
    assert payload["whatsapp"]["state"].startswith("unknown:")
    assert payload["whatsapp"]["message_id"] is None
    assert "delivered" not in (payload["whatsapp"]["state"] or "")
    assert "accepted" not in (payload["whatsapp"]["state"] or "")
    stored = _attempt_rows(tmp_path)
    assert len(stored) == 1 and stored[0][2] is None
    assert client.post(f"/api/notifications/{hvac['id']}/whatsapp").status_code == 200
    assert len(fake.calls) == 1


def test_whatsapp_201_with_id_is_accepted(tmp_path, monkeypatch):
    _live_env(monkeypatch)
    fake = _FakeHttp(status=201, payload={"messages": [{"id": "wamid.ACCEPTED"}]})
    monkeypatch.setattr(whatsapp, "_http_post", fake)
    client = _client(tmp_path, monkeypatch)
    _, hvac = _hvac_notice(client, fake)
    resp = client.post(f"/api/notifications/{hvac['id']}/whatsapp")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["whatsapp"]["state"] == "accepted_by_api"
    assert payload["whatsapp"]["message_id"] == "wamid.ACCEPTED"


def test_whatsapp_malformed_bodies_are_unknown(tmp_path, monkeypatch):
    cases = [
        ["not-a-dict"],
        [],
        "just-a-string",
        {"messages": []},
        {"messages": ["malformed"]},
        {"messages": [["nested"]]},
        {"messages": [{}]},
        {"messages": [{"id": ""}]},
        {"messages": [{"id": "  "}]},
        {"messages": [{"id": 5}]},
        {"messages": [{"noid": 1}]},
    ]
    for payload in cases:
        _live_env(monkeypatch)
        fake = _FakeHttp(payload=payload)
        monkeypatch.setattr(whatsapp, "_http_post", fake)
        client = _client(tmp_path, monkeypatch)
        _, hvac = _hvac_notice(client, fake)
        resp = client.post(f"/api/notifications/{hvac['id']}/whatsapp")
        assert resp.status_code == 200, payload
        body = resp.get_json()
        assert body["whatsapp"]["state"].startswith("unknown:"), payload
        assert body["whatsapp"]["message_id"] is None, payload
        (tmp_path / "api.db").unlink()


def test_whatsapp_transport_and_json_errors_are_failed(tmp_path, monkeypatch):
    for error in (RuntimeError("connection reset (test)"), ValueError("No JSON (test)")):
        _live_env(monkeypatch)
        fake = _FakeHttp(error=error)
        monkeypatch.setattr(whatsapp, "_http_post", fake)
        client = _client(tmp_path, monkeypatch)
        _, hvac = _hvac_notice(client, fake)
        resp = client.post(f"/api/notifications/{hvac['id']}/whatsapp")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["whatsapp"]["state"].startswith("failed:transport_error"), error
        assert body["whatsapp"]["message_id"] is None
        (tmp_path / "api.db").unlink()


def test_whatsapp_exception_after_claim_persists_unknown(tmp_path, monkeypatch):
    _live_env(monkeypatch)
    fake = _FakeHttp()
    monkeypatch.setattr(whatsapp, "_http_post", fake)
    client = _client(tmp_path, monkeypatch)
    _, hvac = _hvac_notice(client, fake)

    def explode(*args, **kwargs):
        raise RuntimeError("boom after claim (test)")

    monkeypatch.setattr(whatsapp, "send_text_message", explode)
    resp = client.post(f"/api/notifications/{hvac['id']}/whatsapp")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["delivery"]["attempted"] is True
    assert body["whatsapp"]["state"].startswith("unknown:")
    assert body["whatsapp"]["message_id"] is None
    assert fake.calls == []
    assert len(_attempt_rows(tmp_path)) == 1
    resp = client.post(f"/api/notifications/{hvac['id']}/whatsapp")
    assert resp.get_json()["delivery"]["reason"] == "already_attempted"
    assert fake.calls == []


def test_whatsapp_repeat_and_concurrent_never_resend(tmp_path, monkeypatch):
    _live_env(monkeypatch)
    fake = _FakeHttp()
    monkeypatch.setattr(whatsapp, "_http_post", fake)
    client = _client(tmp_path, monkeypatch)
    _, hvac = _hvac_notice(client, fake)
    assert client.post(f"/api/notifications/{hvac['id']}/whatsapp").status_code == 200
    assert len(fake.calls) == 1
    for _ in range(3):
        resp = client.post(f"/api/notifications/{hvac['id']}/whatsapp")
        assert resp.get_json()["delivery"]["reason"] == "already_attempted"
    assert len(fake.calls) == 1
    from aria_home.store import Store

    store = Store(path=tmp_path / "other.db")
    notice = {"id": "notif-race-probe", "audience": "hvac_company", "state": "simulated_delivered", "payload": {"audience": "hvac_company"}}
    claimed, _ = store.claim_whatsapp_attempt(notice["id"])
    assert claimed is True
    result = whatsapp.attempt_hvac_whatsapp_delivery(store, notice, http_post=fake)
    assert result == {"attempted": False, "reason": "already_attempted", "state": "pending"}
    assert len(fake.calls) == 1


def test_whatsapp_state_and_ui_wording(tmp_path, monkeypatch):
    assert whatsapp.ACCEPTED_NOTICE.startswith("Accepted by the WhatsApp API")
    assert "not confirmed" in whatsapp.ACCEPTED_NOTICE
    assert "never resends" in whatsapp.UNKNOWN_NOTICE
    assert whatsapp.SIMULATED_NOTICE == "Simulated, no message was sent"
    _live_env(monkeypatch)
    fake = _FakeHttp()
    monkeypatch.setattr(whatsapp, "_http_post", fake)
    client = _client(tmp_path, monkeypatch)
    _, hvac = _hvac_notice(client, fake)
    assert client.post(f"/api/notifications/{hvac['id']}/whatsapp").status_code == 200
    body = fake.calls[0]["body"]
    assert set(body) == {"messaging_product", "to", "type", "text"}
    assert body["to"] == RECIPIENT
    assert body["text"]["body"].splitlines()[0] == "ARIA Home test (synthetic scenario)"


# Finding 9: visual image URLs are properly encoded and fetchable.
AT_Z = "2026-01-17T04:00:00Z"
AT_POSITIVE = "2026-01-16T23:00:00-05:00"
AT_NEGATIVE = "2026-01-16T18:00:00-05:00"


def _visual_at(client, at):
    resp = client.get(f"/api/visual?scenario=visual_water_low_temp_v1&at={at}")
    assert resp.status_code == 200, at
    return resp.get_json()["visual"]


def test_visual_image_url_zulu_is_encoded_and_fetchable(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    visual = _visual_at(client, AT_Z)
    url = visual["image_url"]
    assert "+00:00" not in url
    assert "%2B00%3A00" in url
    image = client.get(url)
    assert image.status_code == 200
    assert image.content_type == "image/webp"
    assert image.data == (VISUAL_FIXTURES / "v1-water-floor.webp").read_bytes()


def test_visual_equivalent_instants_same_bytes(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    first = client.get(_visual_at(client, AT_Z)["image_url"])
    second = client.get(_visual_at(client, AT_POSITIVE)["image_url"])
    assert first.status_code == 200 and second.status_code == 200
    assert first.data == second.data
    assert len(first.data) > 0


def test_visual_negative_offset_url_fetchable(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    visual = _visual_at(client, AT_NEGATIVE)
    parsed = urlparse(visual["image_url"])
    assert parsed.path == "/api/visual/image"
    assert dict(parse_qsl(parsed.query))["scenario"] == "visual_water_low_temp_v1"
    image = client.get(visual["image_url"])
    assert image.status_code == 200
    assert image.data == (VISUAL_FIXTURES / "v1-water-floor.webp").read_bytes()


def test_visual_invalid_timestamps_are_4xx(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    for path in (
        "/api/visual?scenario=visual_water_low_temp_v1&at=bogus",
        "/api/visual?scenario=visual_water_low_temp_v1&at=2026-01-16T18:00:00",
        "/api/visual/image?scenario=visual_water_low_temp_v1&at=bogus",
        "/api/visual/image?scenario=visual_water_low_temp_v1&at=2026-01-16T18:00:00",
        "/api/visual/image?scenario=visual_water_low_temp_v1&at=",
    ):
        assert client.get(path).status_code == 400, path
