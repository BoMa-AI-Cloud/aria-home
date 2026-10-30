"""One-time owner sign-in for the optional Nest camera snapshot.

Run on the owner's Windows machine, signed in to Google as the Device Access
account. It opens Google's Nest consent page, receives the one-time code on
127.0.0.1:8765, exchanges it, and stores ONLY the refresh token as the
Windows user environment variable NEST_REFRESH_TOKEN. It never prints a
token, code or secret; it prints the camera names it can see so the owner
can set NEST_DEVICE_NAME.

    python backend/scripts/nest_auth.py
"""
import os
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from aria_home.nest import TOKEN_URL, _default_http_get, _default_http_post, list_cameras  # noqa: E402

REDIRECT_URI = "http://127.0.0.1:8765/callback"
SCOPE = "https://www.googleapis.com/auth/sdm.service"
CALLBACK_TIMEOUT_S = 300


def consent_url(project_id, client_id):
    query = urllib.parse.urlencode({
        "redirect_uri": REDIRECT_URI,
        "access_type": "offline",
        "prompt": "consent",
        "client_id": client_id,
        "response_type": "code",
        "scope": SCOPE,
    })
    return f"https://nestservices.google.com/partnerconnections/{project_id}/auth?{query}"


def _default_wait_for_code():
    from http.server import BaseHTTPRequestHandler, HTTPServer

    holder = {"code": None, "error": None}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return
            query = urllib.parse.parse_qs(parsed.query)
            if query.get("error"):
                holder["error"] = query["error"][0]
            elif query.get("code"):
                holder["code"] = query["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body>ARIA Home: you can close this tab.</body></html>")

        def log_message(self, format, *args):
            return

    server = HTTPServer(("127.0.0.1", 8765), Handler)
    server.timeout = 1
    deadline = time.time() + CALLBACK_TIMEOUT_S
    try:
        while time.time() < deadline and not (holder["code"] or holder["error"]):
            server.handle_request()
    finally:
        server.server_close()
    return holder["code"], holder["error"]


def _default_save_secret(name, value):
    import ctypes
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    result = ctypes.c_ulong()
    ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x1A, 0, "Environment", 0x0002, 5000, ctypes.byref(result))


def main(argv=None, *, http_post=None, http_get=None, open_browser=None, wait_for_code=None, save_secret=None, out=print):
    post = http_post or _default_http_post
    get = http_get or _default_http_get
    values = {}
    for name in ("NEST_PROJECT_ID", "NEST_CLIENT_ID", "NEST_CLIENT_SECRET"):
        value = (os.environ.get(name) or "").strip()
        if not value:
            out(f"Missing environment variable: {name}")
            return 1
        values[name] = value

    url = consent_url(values["NEST_PROJECT_ID"], values["NEST_CLIENT_ID"])
    try:
        (open_browser or webbrowser.open)(url)
    except Exception:
        pass
    out("Open this link if the browser did not open:")
    out(url)

    try:
        code, error = (wait_for_code or _default_wait_for_code)()
    except OSError:
        out("Could not listen on 127.0.0.1:8765 (is another copy running?)")
        return 1
    if error:
        out(f"Authorization error: {error}")
        return 1
    if not code:
        out("Timed out waiting for Google's callback")
        return 1

    status, body = post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": values["NEST_CLIENT_ID"],
        "client_secret": values["NEST_CLIENT_SECRET"],
        "redirect_uri": REDIRECT_URI,
    })
    if status != 200:
        out(f"Token exchange failed: HTTP {status}")
        return 1
    refresh_token = body.get("refresh_token")
    access_token = body.get("access_token")
    if not refresh_token or not access_token:
        out("Google returned no refresh token (sign in again with prompt=consent)")
        return 1

    try:
        (save_secret or _default_save_secret)("NEST_REFRESH_TOKEN", refresh_token)
    except Exception:
        out("Failed to save NEST_REFRESH_TOKEN")
        return 1
    out("saved NEST_REFRESH_TOKEN")

    cameras, list_status = list_cameras({"project_id": values["NEST_PROJECT_ID"]}, access_token, get)
    if list_status != "ok":
        out(f"Could not list cameras: {list_status}")
        return 1
    out("Cameras found:")
    for camera in cameras:
        out(camera["display_name"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
