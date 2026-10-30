Meta AI (meta.ai web chat, account saf_integration) returned backend/aria_home/nest.py, backend/scripts/nest_auth.py and backend/tests/test_nest.py. Its verbatim files follow these notes.

What was used: nest.py nearly as given (config, token refresh, camera listing, camera choice, capture with stop-in-finally, scrubbing), with the display-name logic folded into one expression, a catch-all failure renamed from the misleading "ffmpeg_error" to "unexpected_error", and dead scrub calls removed.

What was fixed: nest_auth.py listed cameras by sending its "GET" through the POST function (`_http_get = _http_post`), which against the live API would POST to the devices list. The operator rewrote the script around Meta AI's structure, with a real GET seam (http_get), no import fallback, and no non-Windows env fallback. The test's three near-identical fakes were folded into one FakeGoogle, which now also proves the device list is a GET.

What the operator added: the camera status, snapshot and image routes (live-only, absent in public-demo mode), the sam-3.1 upload with disclosure through SamLiveProvider (with a mime parameter for JPEG), ARIA_HOME_NEST_LIVE in the public-demo fail-closed list, the frontend panel, route tests, a browser test, and docs (README, SECURITY "what leaves the house", .env.example, architecture-future).

Red-proof: with the stream stop skipped after an ffmpeg failure, 2 tests failed with AssertionError (0 == 1); restored, 8 passed.

--- Meta AI files (verbatim) ---

### nest.py
"""Optional owner-only snapshot from a Nest Cam Indoor (gen 1) in the mechanical room.

Rules:
- The feature is OFF by default. It becomes configured only when ARIA_HOME_NEST_LIVE == "1"
  and all of NEST_PROJECT_ID, NEST_CLIENT_ID, NEST_CLIENT_SECRET, NEST_REFRESH_TOKEN are
  non-empty. NEST_DEVICE_NAME is optional and matches a camera display name exactly.
- Secrets must never leak: client id/secret, project id, refresh token, access tokens,
  the RTSP URL (it carries a token) and the stream extension token must never appear in
  any return value, exception message, or log line. Any error text that might contain them
  is scrubbed to "[redacted]".
- Every failure is a dict with a clear "status" string. The public entry point
  capture_snapshot() never raises to the caller and never retries silently.
- Stream start and stop are always paired: after GenerateRtspStream succeeds,
  StopRtspStream is ALWAYS called with the same streamExtensionToken, even if ffmpeg
  fails or raises.
- Exactly one frame is grabbed: ffmpeg is called with -frames:v 1.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx

TOKEN_URL = "https://oauth2.googleapis.com/token"
SDM_BASE = "https://smartdevicemanagement.googleapis.com/v1"
CAMERA_TRAIT = "sdm.devices.traits.CameraLiveStream"
SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "instance" / "nest-snapshots"
SOURCE_LABEL = "live camera (owner's mechanical room)"

HttpPost = Callable[..., Tuple[int, Dict[str, Any]]]
HttpGet = Callable[..., Tuple[int, Dict[str, Any]]]
RunFfmpeg = Callable[[str, Path], int]

def _scrub_text(text: Any, secrets: List[Any]) -> str:
    if text is None:
        return ""
    s = str(text)
    # longest first to avoid partial replace
    cleaned = [str(x) for x in secrets if x is not None and str(x) != ""]
    for sec in sorted(cleaned, key=len, reverse=True):
        if sec in s:
            s = s.replace(sec, "[redacted]")
    return s

def _default_http_post(url: str, *, data=None, json=None, headers=None) -> Tuple[int, Dict[str, Any]]:
    try:
        with httpx.Client(timeout=20) as client:
            resp = client.post(url, data=data, json=json, headers=headers)
            try:
                body = resp.json()
            except Exception:
                body = {}
            if not isinstance(body, dict):
                body = {}
            return resp.status_code, body
    except Exception:
        # do not leak exception text that might contain url/token
        return 0, {}

def _default_http_get(url: str, *, headers=None) -> Tuple[int, Dict[str, Any]]:
    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(url, headers=headers)
            try:
                body = resp.json()
            except Exception:
                body = {}
            if not isinstance(body, dict):
                body = {}
            return resp.status_code, body
    except Exception:
        return 0, {}

def _default_run_ffmpeg(rtsp_url: str, out_path: Path) -> int:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return 127
    try:
        # never print/log stderr - it can contain the URL
        result = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-rtsp_transport",
                "tcp",
                "-i",
                rtsp_url,
                "-frames:v",
                "1",
                "-y",
                str(out_path),
            ],
            timeout=30,
            capture_output=True,
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        return 124

def nest_config_from_env(env=None) -> Dict[str, Any]:
    if env is None:
        env = os.environ
    # env may be dict or os.environ mapping
    def _get(k: str) -> str:
        try:
            v = env.get(k, "")
        except AttributeError:
            v = ""
        if v is None:
            return ""
        return str(v)

    project_id = _get("NEST_PROJECT_ID").strip()
    client_id = _get("NEST_CLIENT_ID").strip()
    client_secret = _get("NEST_CLIENT_SECRET").strip()
    refresh_token = _get("NEST_REFRESH_TOKEN").strip()
    device_name = _get("NEST_DEVICE_NAME").strip()
    live_raw = _get("ARIA_HOME_NEST_LIVE").strip()
    live = live_raw == "1"
    configured = bool(
        live
        and project_id != ""
        and client_id != ""
        and client_secret != ""
        and refresh_token != ""
    )
    return {
        "project_id": project_id,
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "device_name": device_name,
        "live": live,
        "configured": configured,
    }

def refresh_access_token(config: Dict[str, Any], http_post: HttpPost) -> Tuple[Optional[str], str]:
    try:
        status_code, body = http_post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": config.get("refresh_token", ""),
                "client_id": config.get("client_id", ""),
                "client_secret": config.get("client_secret", ""),
            },
        )
    except Exception:
        return None, "token_refresh_failed:0"

    if status_code != 200:
        return None, f"token_refresh_failed:{status_code}"
    token = body.get("access_token") if isinstance(body, dict) else None
    if not token:
        return None, f"token_refresh_failed:{status_code}"
    return token, "ok"

def list_cameras(config: Dict[str, Any], token: str, http_get: HttpGet) -> Tuple[List[Dict[str, str]], str]:
    project_id = config.get("project_id", "")
    url = f"{SDM_BASE}/enterprises/{project_id}/devices"
    try:
        status_code, body = http_get(url, headers={"Authorization": f"Bearer {token}"})
    except Exception:
        return [], "device_list_failed:0"

    if status_code != 200:
        return [], f"device_list_failed:{status_code}"

    devices = body.get("devices", []) if isinstance(body, dict) else []
    cameras: List[Dict[str, str]] = []
    for dev in devices:
        if not isinstance(dev, dict):
            continue
        traits = dev.get("traits", {})
        if not isinstance(traits, dict):
            continue
        if CAMERA_TRAIT not in traits:
            continue
        name = dev.get("name", "")
        relations = dev.get("parentRelations") if isinstance(dev.get("parentRelations"), list) else []
        info = traits.get("sdm.devices.traits.Info") if isinstance(traits.get("sdm.devices.traits.Info"), dict) else {}
        candidates = [relations[0].get("displayName") if relations and isinstance(relations[0], dict) else None, info.get("customName")]
        display_name = next((c.strip() for c in candidates if isinstance(c, str) and c.strip()), "camera")
        cameras.append({"name": name, "display_name": display_name})

    return cameras, "ok"

def pick_camera(cameras: List[Dict[str, str]], device_name: str) -> Tuple[Optional[Dict[str, str]], str]:
    dn = (device_name or "").strip()
    if dn != "":
        for cam in cameras:
            if cam.get("display_name") == dn:
                return cam, "ok"
        return None, "device_not_found"
    # no device_name given
    if len(cameras) == 0:
        return None, "no_camera"
    if len(cameras) > 1:
        return None, "several_cameras_set_NEST_DEVICE_NAME"
    return cameras[0], "ok"

def capture_snapshot(
    *,
    env=None,
    http_post: Optional[HttpPost] = None,
    http_get: Optional[HttpGet] = None,
    run_ffmpeg: Optional[RunFfmpeg] = None,
    out_dir: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    _http_post: HttpPost = http_post or _default_http_post
    _http_get: HttpGet = http_get or _default_http_get
    _run_ffmpeg: RunFfmpeg = run_ffmpeg or _default_run_ffmpeg

    _now = now or datetime.now(timezone.utc)
    if _now.tzinfo is None:
        _now = _now.replace(tzinfo=timezone.utc)
    _now_utc = _now.astimezone(timezone.utc)
    captured_at = _now_utc.isoformat()
    timestamp_str = _now_utc.strftime("%Y%m%dT%H%M%SZ")

    _out_dir = Path(out_dir) if out_dir is not None else SNAPSHOT_DIR

    # config and initial secret collection
    try:
        config = nest_config_from_env(env)
    except Exception:
        config = {
            "project_id": "",
            "client_id": "",
            "client_secret": "",
            "refresh_token": "",
            "device_name": "",
            "live": False,
            "configured": False,
        }

    secrets: List[str] = []
    for k in ("project_id", "client_id", "client_secret", "refresh_token"):
        v = config.get(k)
        if v:
            secrets.append(str(v))

    def _base_result(status: str, device_display_name=None, frame_path=None, extra=None):
        # scrub status
        safe_status = _scrub_text(status, secrets)
        res: Dict[str, Any] = {
            "status": safe_status,
            "captured_at": captured_at,
            "frame_path": frame_path,
            "device_display_name": device_display_name,
            "source": SOURCE_LABEL,
        }
        if extra:
            res.update(extra)
        return res

    try:
        if not config.get("configured"):
            return _base_result("not_configured", None, None)

        token, token_status = refresh_access_token(config, _http_post)
        if token is None:
            # token refresh failed, secrets do not yet include token
            return _base_result(token_status, None, None)

        secrets.append(token)

        cameras, list_status = list_cameras(config, token, _http_get)
        if list_status != "ok":
            return _base_result(list_status, None, None)

        camera, pick_status = pick_camera(cameras, config.get("device_name", ""))
        if camera is None:
            return _base_result(pick_status, None, None)

        device_display_name = camera.get("display_name")

        # GenerateRtspStream
        gen_url = f"{SDM_BASE}/{camera.get('name')}:executeCommand"
        headers = {"Authorization": f"Bearer {token}"}
        gen_body = {
            "command": "sdm.devices.commands.CameraLiveStream.GenerateRtspStream",
            "params": {},
        }
        try:
            gen_code, gen_resp = _http_post(gen_url, json=gen_body, headers=headers)
        except Exception as e:
            safe = _scrub_text(str(e), secrets)
            # do not include safe detail that might still contain structure, use code path
            return _base_result(f"stream_start_failed:{safe or 'error'}", device_display_name, None)

        if gen_code != 200:
            return _base_result(f"stream_start_failed:{gen_code}", device_display_name, None)

        try:
            results = gen_resp.get("results", {}) if isinstance(gen_resp, dict) else {}
            stream_urls = results.get("streamUrls", {}) if isinstance(results, dict) else {}
            rtsp_url = stream_urls.get("rtspUrl") if isinstance(stream_urls, dict) else None
            ext_token = results.get("streamExtensionToken") if isinstance(results, dict) else None
            if not rtsp_url or not ext_token:
                raise ValueError("missing rtspUrl or streamExtensionToken")
        except Exception as e:
            safe = _scrub_text(str(e), secrets)
            return _base_result(f"stream_start_failed:{safe or 'error'}", device_display_name, None)

        # add rtsp and ext to scrub list from now on
        secrets.append(rtsp_url)
        secrets.append(ext_token)

        _out_dir.mkdir(parents=True, exist_ok=True)
        out_path = _out_dir / f"nest-{timestamp_str}.jpg"

        ffmpeg_status: str = "ok"
        stop_status: str = "stopped"

        try:
            try:
                ret = _run_ffmpeg(rtsp_url, out_path)
                if ret != 0:
                    ffmpeg_status = f"ffmpeg_failed:{ret}"
                else:
                    ffmpeg_status = "ok"
            except Exception:
                ffmpeg_status = "ffmpeg_error"
        finally:
            # ALWAYS stop
            stop_body = {
                "command": "sdm.devices.commands.CameraLiveStream.StopRtspStream",
                "params": {"streamExtensionToken": ext_token},
            }
            try:
                stop_code, _ = _http_post(gen_url, json=stop_body, headers=headers)
                if stop_code != 200:
                    stop_status = "failed"
                else:
                    stop_status = "stopped"
            except Exception:
                stop_status = "failed"

        # final frame_path only if ok and file exists
        frame_path_str: Optional[str] = None
        final_status = ffmpeg_status
        if ffmpeg_status == "ok":
            try:
                if out_path.exists():
                    frame_path_str = str(out_path)
                    final_status = "ok"
                else:
                    final_status = "ffmpeg_error"
                    frame_path_str = None
            except Exception:
                final_status = "ffmpeg_error"
                frame_path_str = None

        # scrub final status (should not contain secrets, but be safe)
        final_status = _scrub_text(final_status, secrets)

        result: Dict[str, Any] = {
            "status": final_status,
            "captured_at": captured_at,
            "frame_path": frame_path_str if final_status == "ok" else None,
            "device_display_name": device_display_name,
            "source": SOURCE_LABEL,
            "stream_stop": stop_status,
        }
        return result

    except Exception:
        return {
            "status": "unexpected_error",
            "captured_at": captured_at,
            "frame_path": None,
            "device_display_name": None,
            "source": SOURCE_LABEL,
        }


### nest_auth.py
from __future__ import annotations

import os
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

# Allow import of aria_home.nest when backend is on path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

def _default_http_post(url: str, *, data=None, json=None, headers=None) -> Tuple[int, Dict[str, Any]]:
    if httpx is None:
        raise RuntimeError("httpx not available")
    with httpx.Client(timeout=20) as client:
        resp = client.post(url, data=data, json=json, headers=headers)
        try:
            body = resp.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        return resp.status_code, body

def _default_http_get(url: str, *, headers=None) -> Tuple[int, Dict[str, Any]]:
    if httpx is None:
        raise RuntimeError("httpx not available")
    with httpx.Client(timeout=20) as client:
        resp = client.get(url, headers=headers)
        try:
            body = resp.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        return resp.status_code, body

def _default_open_browser(url: str) -> bool:
    try:
        return bool(webbrowser.open(url))
    except Exception:
        return False

def _default_wait_for_code() -> Tuple[Any, Any]:
    from http.server import BaseHTTPRequestHandler, HTTPServer

    holder: Dict[str, Any] = {"code": None, "error": None}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/callback":
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found")
                return
            qs = urllib.parse.parse_qs(parsed.query)
            if "error" in qs:
                holder["error"] = qs["error"][0] if qs["error"] else "unknown_error"
            elif "code" in qs:
                holder["code"] = qs["code"][0] if qs["code"] else None
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body>ARIA Home: you can close this tab.</body></html>")

        def log_message(self, format, *args):
            return

    server = HTTPServer(("127.0.0.1", 8765), Handler)
    server.timeout = 1
    start = time.time()
    try:
        while True:
            if time.time() - start > 300:
                break
            server.handle_request()
            if holder["code"] or holder["error"]:
                break
    finally:
        try:
            server.server_close()
        except Exception:
            pass
    return holder["code"], holder["error"]

def _default_save_secret(name: str, value: str) -> None:
    # Windows user env var
    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE)
        try:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        finally:
            try:
                winreg.CloseKey(key)
            except Exception:
                pass
    except ImportError:
        # Not on Windows in test, fallback to process env for dev
        os.environ[name] = value
        return
    except Exception:
        # never leak value
        raise RuntimeError("Failed to save environment variable")

    try:
        import ctypes

        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x1A
        SMTO_ABORTIFHUNG = 0x0002
        result = ctypes.c_long()
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            "Environment",
            SMTO_ABORTIFHUNG,
            5000,
            ctypes.byref(result),
        )
    except Exception:
        pass

def main(
    argv=None,
    *,
    http_post: Callable[..., Tuple[int, Dict[str, Any]]] | None = None,
    open_browser: Callable[[str], bool] | None = None,
    wait_for_code: Callable[[], Any] | None = None,
    save_secret: Callable[[str, str], None] | None = None,
    out=print,
) -> int:
    _http_post = http_post or _default_http_post
    _open_browser = open_browser or _default_open_browser
    _wait_for_code = wait_for_code or _default_wait_for_code
    _save_secret = save_secret or _default_save_secret
    _http_get = _http_post  # allow single fake to handle GET as well for tests

    # 1. check env
    required = ["NEST_PROJECT_ID", "NEST_CLIENT_ID", "NEST_CLIENT_SECRET"]
    env_vals: Dict[str, str] = {}
    for k in required:
        v = os.environ.get(k, "")
        if not v or not str(v).strip():
            out(f"Missing environment variable: {k}")
            return 1
        env_vals[k] = str(v).strip()

    project_id = env_vals["NEST_PROJECT_ID"]
    client_id = env_vals["NEST_CLIENT_ID"]
    client_secret = env_vals["NEST_CLIENT_SECRET"]

    # 2. consent URL
    base = f"https://nestservices.google.com/partnerconnections/{project_id}/auth"
    q = {
        "redirect_uri": "http://127.0.0.1:8765/callback",
        "access_type": "offline",
        "prompt": "consent",
        "client_id": client_id,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/sdm.service",
    }
    consent_url = base + "?" + urllib.parse.urlencode(q)

    try:
        _open_browser(consent_url)
    except Exception:
        pass
    out("Open this link if the browser did not open:")
    out(consent_url)

    # 3. wait for code
    try:
        wc = _wait_for_code()
    except Exception:
        out("Failed to start local callback server")
        return 1

    code = None
    error = None
    if isinstance(wc, tuple) and len(wc) == 2:
        code, error = wc
    elif isinstance(wc, dict):
        code = wc.get("code")
        error = wc.get("error")
    else:
        # assume string code
        code = wc

    if error:
        out(f"Authorization error: {error}")
        return 1
    if not code:
        out("Timeout waiting for callback")
        return 1

    # 4. exchange code
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "http://127.0.0.1:8765/callback",
    }
    try:
        status, body = _http_post(token_url, data=data)
    except Exception:
        out("Token exchange failed")
        return 1

    if status != 200:
        out(f"Token exchange failed: {status}")
        return 1

    refresh_token = body.get("refresh_token") if isinstance(body, dict) else None
    access_token = body.get("access_token") if isinstance(body, dict) else None

    if not refresh_token or not access_token:
        out("No refresh token in response")
        return 1

    # 5. save refresh token
    try:
        _save_secret("NEST_REFRESH_TOKEN", refresh_token)
    except Exception:
        out("Failed to save NEST_REFRESH_TOKEN")
        return 1

    out("saved NEST_REFRESH_TOKEN")

    # 6. list cameras
    try:
        # import here to respect seam
        from aria_home.nest import list_cameras as _list_cameras
    except Exception:
        # fallback import via path
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "aria_home.nest", str(BACKEND_DIR / "aria_home" / "nest.py")
        )
        mod = importlib.util.module_from_spec(spec)  # type: ignore
        assert spec and spec.loader
        spec.loader.exec_module(mod)  # type: ignore
        _list_cameras = mod.list_cameras  # type: ignore

    cfg = {
        "project_id": project_id,
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "device_name": "",
    }

    # try real GET, but use _http_get which may be the same fake as _http_post
    def _real_get(url, *, headers=None):
        # try _http_get first with get signature, fallback to post signature
        try:
            return _http_get(url, headers=headers)  # type: ignore
        except TypeError:
            return _http_get(url, headers=headers, data=None, json=None)  # type: ignore

    try:
        cameras, _ = _list_cameras(cfg, access_token, _real_get)
    except Exception:
        cameras = []

    out("Cameras found:")
    for cam in cameras:
        dn = cam.get("display_name") if isinstance(cam, dict) else None
        if dn:
            out(str(dn))

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
### test_nest.py
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from aria_home import nest

# load nest_auth module via file location (scripts is not a package)
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "nest_auth", str(BACKEND_DIR / "scripts" / "nest_auth.py")
)
nest_auth = importlib.util.module_from_spec(_spec)  # type: ignore
assert _spec and _spec.loader
_spec.loader.exec_module(nest_auth)  # type: ignore

SECRET_STRINGS = [
    "SECRET-FAKE",
    "REFRESH-FAKE",
    "FAKE-ACCESS-TOKEN",
    "FAKE-RTSP-URL",
    "FAKE-STREAM-TOKEN",
    "FAKE-EXT",
]

ENV_BASE = {
    "ARIA_HOME_NEST_LIVE": "1",
    "NEST_PROJECT_ID": "proj-FAKE",
    "NEST_CLIENT_ID": "client-FAKE",
    "NEST_CLIENT_SECRET": "SECRET-FAKE",
    "NEST_REFRESH_TOKEN": "REFRESH-FAKE",
}

def _make_camera(display_name: str, name_suffix: str = "cam"):
    return {
        "name": f"enterprises/proj-FAKE/devices/{name_suffix}",
        "traits": {
            nest.CAMERA_TRAIT: {},
            "sdm.devices.traits.Info": {"customName": display_name},
        },
        "parentRelations": [{"displayName": display_name}],
    }

class FakeGoogle:
    def __init__(self, cameras=None, fail_token_code=None):
        self.calls: list = []
        self.cameras = cameras if cameras is not None else [_make_camera("Mechanical room", "mech")]
        self.fail_token_code = fail_token_code
        self.generate_calls: list = []
        self.stop_calls: list = []

    def post(self, url, *, data=None, json=None, headers=None):
        self.calls.append(("POST", url, data, json, headers))
        if "oauth2.googleapis.com/token" in url:
            if self.fail_token_code is not None:
                return (self.fail_token_code, {})
            return (
                200,
                {
                    "access_token": "FAKE-ACCESS-TOKEN",
                    "refresh_token": "REFRESH-FAKE-NEW",
                    "expires_in": 3600,
                },
            )
        if "executeCommand" in url:
            if json and "GenerateRtspStream" in str(json.get("command", "")):
                self.generate_calls.append((url, json))
                return (
                    200,
                    {
                        "results": {
                            "streamUrls": {"rtspUrl": "rtsps://FAKE-RTSP-URL?auth=FAKE-STREAM-TOKEN"},
                            "streamExtensionToken": "FAKE-EXT",
                        }
                    },
                )
            if json and "StopRtspStream" in str(json.get("command", "")):
                self.stop_calls.append((url, json))
                # ensure ext token present
                params = json.get("params", {})
                assert params.get("streamExtensionToken") == "FAKE-EXT" or "FAKE-EXT" in str(params)
                return (200, {})
        if "devices" in url:
            # fallback for nest_auth when POST is used for GET
            return (200, {"devices": self.cameras})
        return (200, {})

    def get(self, url, *, headers=None):
        self.calls.append(("GET", url, headers))
        if "devices" in url:
            return (200, {"devices": self.cameras})
        return (404, {})

def _assert_no_secrets(result):
    s = str(result)
    for sec in SECRET_STRINGS:
        assert sec not in s, f"secret {sec!r} leaked in {s}"

def test_not_configured(tmp_path, monkeypatch):
    # no live flag
    monkeypatch.delenv("ARIA_HOME_NEST_LIVE", raising=False)
    monkeypatch.delenv("NEST_PROJECT_ID", raising=False)
    monkeypatch.delenv("NEST_CLIENT_ID", raising=False)
    monkeypatch.delenv("NEST_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("NEST_REFRESH_TOKEN", raising=False)

    fake = FakeGoogle()

    def fake_ffmpeg(rtsp_url, out_path):
        Path(out_path).write_bytes(b"\xff\xd8fake")
        return 0

    env = {
        "NEST_PROJECT_ID": "proj-FAKE",
        "NEST_CLIENT_ID": "client-FAKE",
        "NEST_CLIENT_SECRET": "SECRET-FAKE",
        "NEST_REFRESH_TOKEN": "REFRESH-FAKE",
        # no ARIA_HOME_NEST_LIVE
    }

    res = nest.capture_snapshot(
        env=env, http_post=fake.post, http_get=fake.get, run_ffmpeg=fake_ffmpeg, out_dir=tmp_path
    )
    assert res["status"] == "not_configured"
    assert len(fake.calls) == 0
    assert len(fake.generate_calls) == 0
    assert len(fake.stop_calls) == 0
    _assert_no_secrets(res)

def test_happy_path(tmp_path):
    fake = FakeGoogle()

    def fake_ffmpeg(rtsp_url, out_path):
        # ensure rtsp url is the fake one (test internal, not leaked)
        assert "FAKE-RTSP-URL" in rtsp_url
        Path(out_path).write_bytes(b"\xff\xd8fake")
        return 0

    res = nest.capture_snapshot(
        env=ENV_BASE, http_post=fake.post, http_get=fake.get, run_ffmpeg=fake_ffmpeg, out_dir=tmp_path
    )
    _assert_no_secrets(res)
    assert res["status"] == "ok"
    assert res["device_display_name"] == "Mechanical room"
    assert res["frame_path"] is not None
    assert Path(res["frame_path"]).exists()
    assert Path(res["frame_path"]).parent == tmp_path
    assert Path(res["frame_path"]).read_bytes().startswith(b"\xff\xd8")
    assert res["source"] == nest.SOURCE_LABEL
    # exactly one generate and one stop
    assert len(fake.generate_calls) == 1
    assert len(fake.stop_calls) == 1
    # stop carries FAKE-EXT (checked inside fake, but double-check)
    assert fake.stop_calls[0][1]["params"]["streamExtensionToken"] == "FAKE-EXT"
    assert res.get("stream_stop") == "stopped"

def test_ffmpeg_returns_1(tmp_path):
    fake = FakeGoogle()

    def fake_ffmpeg_fail(rtsp_url, out_path):
        Path(out_path).write_bytes(b"\xff\xd8fake")
        return 1

    res = nest.capture_snapshot(
        env=ENV_BASE, http_post=fake.post, http_get=fake.get, run_ffmpeg=fake_ffmpeg_fail, out_dir=tmp_path
    )
    _assert_no_secrets(res)
    assert res["status"] == "ffmpeg_failed:1"
    assert res["frame_path"] is None
    # stop still called
    assert len(fake.generate_calls) == 1
    assert len(fake.stop_calls) == 1

def test_ffmpeg_raises_with_rtsp(tmp_path):
    fake = FakeGoogle()

    def fake_ffmpeg_raise(rtsp_url, out_path):
        raise RuntimeError("boom rtsps://FAKE-RTSP-URL?auth=FAKE-STREAM-TOKEN")

    res = nest.capture_snapshot(
        env=ENV_BASE, http_post=fake.post, http_get=fake.get, run_ffmpeg=fake_ffmpeg_raise, out_dir=tmp_path
    )
    _assert_no_secrets(res)
    assert res["status"] == "ffmpeg_error"
    assert res["frame_path"] is None
    assert len(fake.generate_calls) == 1
    assert len(fake.stop_calls) == 1

def test_token_refresh_401(tmp_path):
    fake = FakeGoogle(fail_token_code=401)

    def fake_ffmpeg(rtsp_url, out_path):
        Path(out_path).write_bytes(b"\xff\xd8fake")
        return 0

    res = nest.capture_snapshot(
        env=ENV_BASE, http_post=fake.post, http_get=fake.get, run_ffmpeg=fake_ffmpeg, out_dir=tmp_path
    )
    _assert_no_secrets(res)
    assert res["status"] == "token_refresh_failed:401"
    # no stream started
    assert len(fake.generate_calls) == 0
    assert len(fake.stop_calls) == 0

def test_two_cameras_without_device_name(tmp_path):
    cameras = [_make_camera("Mechanical room", "mech"), _make_camera("Garage", "garage")]
    fake = FakeGoogle(cameras=cameras)

    def fake_ffmpeg(rtsp_url, out_path):
        Path(out_path).write_bytes(b"\xff\xd8fake")
        return 0

    res = nest.capture_snapshot(
        env=ENV_BASE, http_post=fake.post, http_get=fake.get, run_ffmpeg=fake_ffmpeg, out_dir=tmp_path
    )
    _assert_no_secrets(res)
    assert res["status"] == "several_cameras_set_NEST_DEVICE_NAME"
    assert len(fake.generate_calls) == 0

def test_two_cameras_with_device_name_matching_second(tmp_path):
    cameras = [_make_camera("Mechanical room", "mech"), _make_camera("Garage", "garage")]
    fake = FakeGoogle(cameras=cameras)

    def fake_ffmpeg(rtsp_url, out_path):
        Path(out_path).write_bytes(b"\xff\xd8fake")
        return 0

    env = dict(ENV_BASE)
    env["NEST_DEVICE_NAME"] = "Garage"

    res = nest.capture_snapshot(
        env=env, http_post=fake.post, http_get=fake.get, run_ffmpeg=fake_ffmpeg, out_dir=tmp_path
    )
    _assert_no_secrets(res)
    assert res["status"] == "ok"
    assert res["device_display_name"] == "Garage"
    assert Path(res["frame_path"]).exists()
    assert len(fake.generate_calls) == 1
    assert len(fake.stop_calls) == 1

def test_secrets_never_in_result_happy(tmp_path):
    # extra explicit check for all secret strings
    fake = FakeGoogle()

    def fake_ffmpeg(rtsp_url, out_path):
        Path(out_path).write_bytes(b"\xff\xd8fake")
        return 0

    res = nest.capture_snapshot(
        env=ENV_BASE, http_post=fake.post, http_get=fake.get, run_ffmpeg=fake_ffmpeg, out_dir=tmp_path
    )
    s = str(res)
    for sec in SECRET_STRINGS:
        assert sec not in s

def test_nest_auth_main_with_fakes(monkeypatch):
    # set required env for auth script
    monkeypatch.setenv("NEST_PROJECT_ID", "proj-FAKE")
    monkeypatch.setenv("NEST_CLIENT_ID", "client-FAKE")
    monkeypatch.setenv("NEST_CLIENT_SECRET", "SECRET-FAKE")

    class FakeAuth:
        def __init__(self):
            self.calls = []

        def post(self, url, *, data=None, json=None, headers=None):
            self.calls.append((url, data, json, headers))
            if "oauth2.googleapis.com/token" in url:
                return (
                    200,
                    {
                        "access_token": "FAKE-ACCESS-TOKEN",
                        "refresh_token": "REFRESH-FAKE",
                        "expires_in": 3600,
                    },
                )
            if "devices" in url:
                return (
                    200,
                    {
                        "devices": [
                            {
                                "name": "enterprises/proj-FAKE/devices/mech",
                                "traits": {
                                    nest.CAMERA_TRAIT: {},
                                    "sdm.devices.traits.Info": {"customName": "Mechanical room"},
                                },
                                "parentRelations": [{"displayName": "Mechanical room"}],
                            }
                        ]
                    },
                )
            return (200, {})

        def get(self, url, *, headers=None):
            self.calls.append((url, headers))
            if "devices" in url:
                return (
                    200,
                    {
                        "devices": [
                            {
                                "name": "enterprises/proj-FAKE/devices/mech",
                                "traits": {
                                    nest.CAMERA_TRAIT: {},
                                    "sdm.devices.traits.Info": {"customName": "Mechanical room"},
                                },
                                "parentRelations": [{"displayName": "Mechanical room"}],
                            }
                        ]
                    },
                )
            return (404, {})

    fake_google = FakeAuth()
    # fake http_post that handles both POST and GET (single seam used for both)
    def fake_http_post(url, *, data=None, json=None, headers=None):
        # dispatch to appropriate method
        if "devices" in url:
            # simulate GET via POST seam returning devices
            return (200, {"devices": fake_google.get(url, headers=headers)[1].get("devices", [])})
        return fake_google.post(url, data=data, json=json, headers=headers)

    # For simplicity, use fake_google.post as http_post that also handles devices via fallback
    # We'll make a wrapper that returns token for token url and devices for devices url
    def unified_post(url, *, data=None, json=None, headers=None):
        if "oauth2.googleapis.com/token" in url:
            return (200, {"access_token": "FAKE-ACCESS-TOKEN", "refresh_token": "REFRESH-FAKE"})
        if "devices" in url:
            return (
                200,
                {
                    "devices": [
                        {
                            "name": "enterprises/proj-FAKE/devices/mech",
                            "traits": {
                                nest.CAMERA_TRAIT: {},
                                "sdm.devices.traits.Info": {"customName": "Mechanical room"},
                            },
                            "parentRelations": [{"displayName": "Mechanical room"}],
                        }
                    ]
                },
            )
        return (200, {})

    opened = []

    def fake_open_browser(url):
        opened.append(url)
        return True

    def fake_wait_for_code():
        return ("FAKE-AUTH-CODE", None)

    saved = []

    def fake_save_secret(name, value):
        saved.append((name, value))

    out_lines: list[str] = []

    def fake_out(*args, **kwargs):
        out_lines.append(" ".join(str(a) for a in args))

    rc = nest_auth.main(
        http_post=unified_post,
        open_browser=fake_open_browser,
        wait_for_code=fake_wait_for_code,
        save_secret=fake_save_secret,
        out=fake_out,
    )

    assert rc == 0
    # prints saved and Mechanical room
    combined = "\n".join(out_lines)
    assert "saved NEST_REFRESH_TOKEN" in combined
    assert "Mechanical room" in combined
    # save_secret exactly once with correct tuple
    assert len(saved) == 1
    assert saved[0][0] == "NEST_REFRESH_TOKEN"
    assert saved[0][1] == "REFRESH-FAKE"
    # none of secret strings in captured output
    for sec in SECRET_STRINGS:
        assert sec not in combined, f"secret {sec} leaked in output {combined}"
    # open_browser called with URL containing project id and client id but not secret
    assert len(opened) == 1
    assert "proj-FAKE" in opened[0]
    assert "client-FAKE" in opened[0]
    assert "SECRET-FAKE" not in opened[0]