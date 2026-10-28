"""Optional WhatsApp Cloud API delivery for the HVAC-company notice.

Off by default. Real delivery happens only when all four environment
variables are set: WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID,
WHATSAPP_TEST_RECIPIENT, plus the explicit opt-in
ARIA_HOME_WHATSAPP_LIVE=1. Otherwise the notice stays exactly as today
(simulated, "Simulated, no message was sent").

Scope: only the hvac_company notice, only after the manager-authorisation
event (the notice only exists in its deliverable state when the
notification gate allowed it), only to WHATSAPP_TEST_RECIPIENT, which
stands in for the HVAC company. The message content is rendered from the
exact payload dict the HVAC allowlist already permits (built by
notifications.build_payload, never copied), as plain text whose first
line is "ARIA Home test (synthetic scenario)".

Idempotency: at most one real send per notification id ever. The attempt
row is persisted before the API call, so replay, refresh, retry or a
second POST never re-sends.

Credentials live only in environment variables. The token is used
in-memory for the Authorization header and is never stored in the
database, responses, logs, attempt rows or ids. The recipient number is
likewise never stored; responses and UI name only "the owner's test
number".
"""

import os
from datetime import datetime, timezone

WHATSAPP_API_HOST = "graph.facebook.com"
WHATSAPP_API_VERSION = "v25.0"
WHATSAPP_MESSAGE_TYPE = "text"
WHATSAPP_FIRST_LINE = "ARIA Home test (synthetic scenario)"
WHATSAPP_RECIPIENT_NOTE = "To the owner's test number on WhatsApp (stands in for the HVAC company)"

REQUIRED_ENV = (
    "WHATSAPP_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "WHATSAPP_TEST_RECIPIENT",
    "ARIA_HOME_WHATSAPP_LIVE",
)

SIMULATED_NOTICE = "Simulated, no message was sent"
DELIVERED_NOTICE = "Sent to the owner's test number on WhatsApp (stands in for the HVAC company)"

OUTSIDE_WINDOW_CODES = (131047,)
OUTSIDE_WINDOW_REASON = "outside_24h_window"


def whatsapp_api_path(phone_number_id):
    return f"/{WHATSAPP_API_VERSION}/{phone_number_id}/messages"


def whatsapp_config_from_env(env=None):
    source = os.environ if env is None else env
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    token = (get("WHATSAPP_TOKEN") or "").strip()
    phone_number_id = (get("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
    test_recipient = (get("WHATSAPP_TEST_RECIPIENT") or "").strip()
    live = (get("ARIA_HOME_WHATSAPP_LIVE") or "").strip() == "1"
    configured = bool(live and token and phone_number_id and test_recipient)
    return {
        "token": token,
        "phone_number_id": phone_number_id,
        "test_recipient": test_recipient,
        "live": live,
        "configured": configured,
    }


def build_hvac_whatsapp_text(payload):
    """Render the allowlisted HVAC payload as plain text.

    Takes the exact payload dict from notifications.build_payload (same
    function, not a copy), so only allowlisted fields can ever appear.
    """
    lines = [WHATSAPP_FIRST_LINE, WHATSAPP_RECIPIENT_NOTE]
    for key, value in sorted((payload or {}).items()):
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"- {item}" for item in value)
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _scrub(text, config):
    cleaned = str(text)
    for secret in (config.get("token"), config.get("test_recipient"), config.get("phone_number_id")):
        if secret:
            cleaned = cleaned.replace(secret, "[redacted]")
    return cleaned


def _default_http_post(url, headers, body):
    import httpx

    response = httpx.post(url, headers=headers, json=body, timeout=30.0)
    try:
        data = response.json()
    except ValueError:
        data = {}
    return response.status_code, data if isinstance(data, dict) else {}


_http_post = _default_http_post


def send_text_message(config, text, http_post=None):
    """POST one text message. Returns (ok, message_id, error_reason)."""
    sender = http_post or _http_post
    url = f"https://{WHATSAPP_API_HOST}{whatsapp_api_path(config['phone_number_id'])}"
    headers = {"Authorization": "Bearer " + config["token"], "Content-Type": "application/json"}
    body = {"messaging_product": "whatsapp", "to": config["test_recipient"], "type": WHATSAPP_MESSAGE_TYPE, "text": {"body": text}}
    try:
        status, data = sender(url, headers, body)
    except Exception as exc:
        return False, None, f"transport_error: {_scrub(exc, config)[:200]}"
    if status in (200, 201):
        messages = data.get("messages") if isinstance(data, dict) else None
        message_id = messages[0].get("id") if messages else None
        return True, str(message_id) if message_id else None, None
    error = data.get("error") if isinstance(data, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    message = error.get("message") if isinstance(error, dict) else ""
    if code in OUTSIDE_WINDOW_CODES or "window" in str(message).lower():
        return False, None, OUTSIDE_WINDOW_REASON
    detail = _scrub(f"{code}: {message}".strip(": "), config)[:200]
    return False, None, f"api_error_{status}: {detail}".rstrip(": ")


def attempt_hvac_whatsapp_delivery(store, notification, *, env=None, http_post=None, recipient=None):
    """Attempt real delivery for one HVAC notice; never raises.

    Returns a small status dict. No HTTP happens unless the channel is
    fully opted in, the notice is an allowed hvac_company notice, and no
    attempt was recorded before.
    """
    if not isinstance(notification, dict) or notification.get("audience") != "hvac_company":
        return {"attempted": False, "reason": "not_hvac_notice"}
    if notification.get("state") != "simulated_delivered":
        return {"attempted": False, "reason": f"notice_not_deliverable:{notification.get('state')}"}
    config = whatsapp_config_from_env(env)
    if not config["configured"]:
        return {"attempted": False, "reason": "not_configured"}
    existing = store.get_whatsapp_attempt(notification["id"])
    if existing is not None:
        return {"attempted": False, "reason": "already_attempted", "state": existing.get("state")}
    if recipient is not None and recipient != config["test_recipient"]:
        store.record_whatsapp_attempt(notification["id"], "refused")
        return {"attempted": False, "reason": "refused:recipient_not_test_number", "state": "refused"}
    claimed, _ = store.claim_whatsapp_attempt(notification["id"])
    if not claimed:
        existing = store.get_whatsapp_attempt(notification["id"]) or {}
        return {"attempted": False, "reason": "already_attempted", "state": existing.get("state")}
    text = build_hvac_whatsapp_text(notification.get("payload") or {})
    ok, message_id, error = send_text_message(config, text, http_post=http_post)
    if ok:
        row = store.update_whatsapp_attempt(notification["id"], "delivered_to_test_number", message_id=message_id)
    else:
        row = store.update_whatsapp_attempt(notification["id"], f"failed:{error or 'unknown'}")
    return {"attempted": True, "state": row["state"], "message_id": row["message_id"]}


def build_whatsapp_audit(payload, authorising_event):
    from .notifications import ALLOWLISTS

    return {
        "channel": "whatsapp_cloud_api",
        "api": {
            "host": WHATSAPP_API_HOST,
            "version": WHATSAPP_API_VERSION,
            "path_template": whatsapp_api_path("{phone_number_id}"),
            "method": "POST",
            "message_type": WHATSAPP_MESSAGE_TYPE,
        },
        "scope": "hvac_company notice only, only after the manager_hvac_authorized event; the recipient is always WHATSAPP_TEST_RECIPIENT, which stands in for the HVAC company; any other recipient is refused and nothing is sent",
        "opt_in_env": list(REQUIRED_ENV),
        "live_requires": "WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_TEST_RECIPIENT all set plus ARIA_HOME_WHATSAPP_LIVE=1; otherwise the notice stays simulated",
        "simulated_notice": SIMULATED_NOTICE,
        "delivered_notice": DELIVERED_NOTICE,
        "first_line": WHATSAPP_FIRST_LINE,
        "fields_sent": sorted(ALLOWLISTS["hvac_company"]),
        "example_text": build_hvac_whatsapp_text(payload),
        "authorising_event": authorising_event,
        "idempotency": "at most one real send per notification id ever; the attempt is persisted before the API call, so replay, refresh, retry or a second POST never re-sends",
        "statuses": ["delivered_to_test_number", "refused", "failed:<reason>"],
        "secrets": "credentials only from environment variables; the token is used in-memory for the Authorization header and never lands in the database, responses, logs, attempt rows or ids; the recipient number is never stored",
    }


def _now_iso():
    return datetime.now(timezone.utc).isoformat()
