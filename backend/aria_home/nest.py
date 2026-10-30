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

