"""Optional Nest snapshot: off by default, stream always stopped, no secret ever returned or printed (day11-14)."""
import importlib.util
from pathlib import Path

from aria_home import nest

BACKEND_DIR = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("nest_auth", BACKEND_DIR / "scripts" / "nest_auth.py")
nest_auth = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nest_auth)

SECRET_STRINGS = ["SECRET-FAKE", "REFRESH-FAKE", "FAKE-ACCESS-TOKEN", "FAKE-RTSP-URL", "FAKE-STREAM-TOKEN", "FAKE-EXT", "FAKE-AUTH-CODE"]
ENV = {
    "ARIA_HOME_NEST_LIVE": "1",
    "NEST_PROJECT_ID": "proj-FAKE",
    "NEST_CLIENT_ID": "client-FAKE",
    "NEST_CLIENT_SECRET": "SECRET-FAKE",
    "NEST_REFRESH_TOKEN": "REFRESH-FAKE",
}


def _camera(display_name, suffix):
    return {
        "name": f"enterprises/proj-FAKE/devices/{suffix}",
        "traits": {nest.CAMERA_TRAIT: {}, "sdm.devices.traits.Info": {"customName": display_name}},
        "parentRelations": [{"displayName": display_name}],
    }


class FakeGoogle:
    def __init__(self, cameras=None, token_status=200):
        self.calls = []
        self.cameras = cameras if cameras is not None else [_camera("Mechanical room", "mech")]
        self.token_status = token_status
        self.generate_calls = []
        self.stop_calls = []

    def post(self, url, *, data=None, json=None, headers=None):
        self.calls.append(("POST", url))
        if url == nest.TOKEN_URL:
            if self.token_status != 200:
                return self.token_status, {}
            return 200, {"access_token": "FAKE-ACCESS-TOKEN", "refresh_token": "REFRESH-FAKE"}
        command = (json or {}).get("command", "")
        if command.endswith("GenerateRtspStream"):
            self.generate_calls.append((url, json))
            return 200, {"results": {"streamUrls": {"rtspUrl": "rtsps://FAKE-RTSP-URL?auth=FAKE-STREAM-TOKEN"}, "streamExtensionToken": "FAKE-EXT"}}
        if command.endswith("StopRtspStream"):
            self.stop_calls.append((url, json))
            return 200, {}
        return 404, {}

    def get(self, url, *, headers=None):
        self.calls.append(("GET", url))
        if url.endswith("/enterprises/proj-FAKE/devices"):
            return 200, {"devices": self.cameras}
        return 404, {}


def _ffmpeg_ok(rtsp_url, out_path):
    Path(out_path).write_bytes(b"\xff\xd8fake")
    return 0


def _snapshot(fake, tmp_path, env=ENV, run_ffmpeg=_ffmpeg_ok):
    result = nest.capture_snapshot(env=env, http_post=fake.post, http_get=fake.get, run_ffmpeg=run_ffmpeg, out_dir=tmp_path)
    for secret in SECRET_STRINGS:
        assert secret not in str(result), secret
    return result


def test_not_configured_makes_zero_calls(tmp_path):
    fake = FakeGoogle()
    env = {k: v for k, v in ENV.items() if k != "ARIA_HOME_NEST_LIVE"}
    assert _snapshot(fake, tmp_path, env=env)["status"] == "not_configured"
    assert fake.calls == []
    assert nest.nest_config_from_env({**ENV, "NEST_CLIENT_SECRET": " "})["configured"] is False


def test_happy_path_grabs_one_frame_and_stops_the_stream(tmp_path):
    fake = FakeGoogle()
    result = _snapshot(fake, tmp_path)
    assert result["status"] == "ok"
    assert result["device_display_name"] == "Mechanical room"
    assert result["source"] == nest.SOURCE_LABEL
    frame = Path(result["frame_path"])
    assert frame.parent == tmp_path and frame.read_bytes().startswith(b"\xff\xd8")
    assert len(fake.generate_calls) == 1
    assert len(fake.stop_calls) == 1
    assert fake.stop_calls[0][1]["params"] == {"streamExtensionToken": "FAKE-EXT"}
    assert result["stream_stop"] == "stopped"


def test_ffmpeg_failure_still_stops_the_stream(tmp_path):
    fake = FakeGoogle()
    result = _snapshot(fake, tmp_path, run_ffmpeg=lambda url, out: 1)
    assert result["status"] == "ffmpeg_failed:1"
    assert result["frame_path"] is None
    assert len(fake.stop_calls) == 1


def test_ffmpeg_exception_with_url_still_stops_and_leaks_nothing(tmp_path):
    fake = FakeGoogle()

    def boom(rtsp_url, out_path):
        raise RuntimeError("boom rtsps://FAKE-RTSP-URL?auth=FAKE-STREAM-TOKEN")

    result = _snapshot(fake, tmp_path, run_ffmpeg=boom)
    assert result["status"] == "ffmpeg_error"
    assert len(fake.stop_calls) == 1


def test_token_refresh_failure_starts_no_stream(tmp_path):
    fake = FakeGoogle(token_status=401)
    assert _snapshot(fake, tmp_path)["status"] == "token_refresh_failed:401"
    assert fake.generate_calls == [] and fake.stop_calls == []


def test_several_cameras_need_a_device_name(tmp_path):
    cameras = [_camera("Mechanical room", "mech"), _camera("Garage", "garage")]
    fake = FakeGoogle(cameras=cameras)
    assert _snapshot(fake, tmp_path)["status"] == "several_cameras_set_NEST_DEVICE_NAME"
    assert fake.generate_calls == []
    chosen = _snapshot(FakeGoogle(cameras=cameras), tmp_path, env={**ENV, "NEST_DEVICE_NAME": "Garage"})
    assert chosen["status"] == "ok" and chosen["device_display_name"] == "Garage"
    assert _snapshot(FakeGoogle(cameras=cameras), tmp_path, env={**ENV, "NEST_DEVICE_NAME": "Attic"})["status"] == "device_not_found"


def test_auth_script_saves_only_the_refresh_token_and_prints_no_secret(monkeypatch):
    for name in ("NEST_PROJECT_ID", "NEST_CLIENT_ID", "NEST_CLIENT_SECRET"):
        monkeypatch.setenv(name, ENV[name])
    fake = FakeGoogle()
    opened, saved, lines = [], [], []
    rc = nest_auth.main(
        http_post=fake.post,
        http_get=fake.get,
        open_browser=opened.append,
        wait_for_code=lambda: ("FAKE-AUTH-CODE", None),
        save_secret=lambda name, value: saved.append((name, value)),
        out=lambda *args: lines.append(" ".join(str(a) for a in args)),
    )
    output = "\n".join(lines)
    assert rc == 0
    assert "saved NEST_REFRESH_TOKEN" in output and "Mechanical room" in output
    assert saved == [("NEST_REFRESH_TOKEN", "REFRESH-FAKE")]
    for secret in SECRET_STRINGS:
        assert secret not in output, secret
    assert ("GET", "https://smartdevicemanagement.googleapis.com/v1/enterprises/proj-FAKE/devices") in fake.calls
    assert len(opened) == 1 and "proj-FAKE" in opened[0] and "SECRET-FAKE" not in opened[0]


def test_auth_script_names_a_missing_variable_without_its_value(monkeypatch):
    monkeypatch.setenv("NEST_PROJECT_ID", ENV["NEST_PROJECT_ID"])
    monkeypatch.setenv("NEST_CLIENT_ID", "")
    monkeypatch.setenv("NEST_CLIENT_SECRET", ENV["NEST_CLIENT_SECRET"])
    lines = []
    assert nest_auth.main(out=lines.append) == 1
    assert lines == ["Missing environment variable: NEST_CLIENT_ID"]


def _app_client(tmp_path, monkeypatch, **env):
    from aria_home.app import create_app

    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    for name in ("ARIA_HOME_NEST_LIVE", "NEST_PROJECT_ID", "NEST_CLIENT_ID", "NEST_CLIENT_SECRET", "NEST_REFRESH_TOKEN", "MODEL_API_KEY"):
        monkeypatch.setenv(name, env.get(name, ""))
    return create_app().test_client()


def test_snapshot_route_off_by_default_makes_zero_calls(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(nest, "capture_snapshot", lambda **kw: calls.append(kw) or {"status": "ok"})
    client = _app_client(tmp_path, monkeypatch)
    resp = client.post("/api/camera/snapshot", json={})
    assert resp.status_code == 409 and resp.get_json()["reason"] == "not_configured"
    assert calls == []
    assert client.get("/api/camera/snapshot").status_code == 405
    assert client.get("/api/camera/status").get_json()["configured"] is False


def test_snapshot_route_without_segment_never_calls_sam(tmp_path, monkeypatch):
    from aria_home import visual

    frame = tmp_path / "nest-20261029T120000Z.jpg"
    frame.write_bytes(b"\xff\xd8fake")
    monkeypatch.setattr(nest, "capture_snapshot", lambda **kw: {"status": "ok", "captured_at": "2026-10-29T12:00:00+00:00", "frame_path": str(frame), "device_display_name": "Mechanical room", "source": nest.SOURCE_LABEL, "stream_stop": "stopped"})
    sam_calls = []
    monkeypatch.setattr(visual.SamLiveProvider, "segment", lambda self, *a, **k: sam_calls.append(a) or {})
    client = _app_client(tmp_path, monkeypatch, **ENV, MODEL_API_KEY="FAKE-MODEL-KEY")
    before = client.get("/api/investigation?scenario=care_home_v1&at=2026-01-17T02:31:00-05:00").get_json()
    body = client.post("/api/camera/snapshot", json={"segment": False}).get_json()
    assert body["camera"]["status"] == "ok"
    assert body["image_url"] == "/api/camera/snapshot/nest-20261029T120000Z.jpg"
    assert "frame_path" not in body["camera"]
    assert body["segmentation"] is None and sam_calls == []
    assert "never evidence" in body["note"]
    after = client.get("/api/investigation?scenario=care_home_v1&at=2026-01-17T02:31:00-05:00").get_json()
    assert before["readiness"]["status"] == "at_risk"
    assert after["readiness"] == before["readiness"]

    segmented = client.post("/api/camera/snapshot", json={"segment": True}).get_json()["segmentation"]
    assert segmented["disclosure"] == "this real image was uploaded to Meta's sam-3.1"
    assert len(sam_calls) == 3
    assert "FAKE-MODEL-KEY" not in str(segmented)


def test_camera_routes_absent_in_public_demo(tmp_path, monkeypatch):
    from aria_home.app import create_app

    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("ARIA_HOME_NEST_LIVE", "")
    client = create_app().test_client()
    assert client.post("/api/camera/snapshot", json={}).status_code == 404
    assert client.get("/api/camera/status").status_code == 404


def test_public_demo_refuses_to_start_with_nest_live(tmp_path, monkeypatch):
    import pytest
    from aria_home.app import create_app

    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("ARIA_HOME_NEST_LIVE", "1")
    with pytest.raises(RuntimeError, match="ARIA_HOME_NEST_LIVE=1"):
        create_app()
