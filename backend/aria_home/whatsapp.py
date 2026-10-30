"""Optional WhatsApp Cloud API delivery for the HVAC-company notice and the caregiver permission request.

Off by default. Real delivery happens only when all four environment
variables are set: WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID,
WHATSAPP_TEST_RECIPIENT, plus the explicit opt-in
ARIA_HOME_WHATSAPP_LIVE=1. Otherwise the notice stays exactly as today
(simulated, "Simulated, no message was sent").

Scope: the hvac_company notice and the family caregiver's permission
request (the caregiver_alert notice, through
attempt_caregiver_permission_whatsapp; the test number then stands in for
the caregiver). The HVAC notice goes only after the manager/caregiver-authorisation
event (the notice only exists in its deliverable state when the
notification gate allowed it), only to WHATSAPP_TEST_RECIPIENT, which
stands in for the HVAC company. The message content is rendered from the
exact payload dict the HVAC allowlist already permits (built by
notifications.build_payload, never copied), as plain text whose first
line is "ARIA Home test (synthetic scenario)".

Idempotency: at most one real send per notification id ever. The attempt
row is persisted before the API call, so replay, refresh, retry or a
second POST never re-sends. An HTTP success code alone is NOT confirmed
delivery: a 200/201 response counts as "accepted by API" only when it
carries a usable message id; anything else is "unknown" (verify manually
on the test phone) or "failed". Unknown and failed attempts are terminal
and never auto-resent; there is no resend shortcut.

Manual reconciliation: if the stored state starts with "unknown", the
API response could not be confirmed — check the owner's test phone for
the message, and do not POST again (a repeat returns already_attempted
without sending).

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
CAREGIVER_RECIPIENT_NOTE = "To the owner's test number on WhatsApp (stands in for the family caregiver)"

REQUIRED_ENV = (
    "WHATSAPP_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "WHATSAPP_TEST_RECIPIENT",
    "ARIA_HOME_WHATSAPP_LIVE",
)

SIMULATED_NOTICE = "Simulated, no message was sent"
ACCEPTED_NOTICE = "Accepted by the WhatsApp API (message id recorded); delivery to the handset is not confirmed"
UNKNOWN_NOTICE = "Delivery unknown — check the test phone manually; the app never resends"
DELIVERED_NOTICE = ACCEPTED_NOTICE

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


def _unconfirmed(detail):
    return f"unconfirmed:{detail}"


def send_text_message(config, text, http_post=None):
    """POST one text message. Returns (ok, message_id, error_reason).

    An HTTP 200/201 is "accepted by API" only when the body is an object
    with a non-empty messages list whose first element is an object with
    a non-empty string id. Anything else on the success path is
    "unconfirmed" (unknown), never success.
    """
    sender = http_post or _http_post
    url = f"https://{WHATSAPP_API_HOST}{whatsapp_api_path(config['phone_number_id'])}"
    headers = {"Authorization": "Bearer " + config["token"], "Content-Type": "application/json"}
    body = {"messaging_product": "whatsapp", "to": config["test_recipient"], "type": WHATSAPP_MESSAGE_TYPE, "text": {"body": text}}
    try:
        status, data = sender(url, headers, body)
    except Exception as exc:
        return False, None, f"transport_error: {_scrub(exc, config)[:200]}"
    if status not in (200, 201):
        error = data.get("error") if isinstance(data, dict) else None
        code = error.get("code") if isinstance(error, dict) else None
        message = error.get("message") if isinstance(error, dict) else ""
        if code in OUTSIDE_WINDOW_CODES or "window" in str(message).lower():
            return False, None, OUTSIDE_WINDOW_REASON
        detail = _scrub(f"{code}: {message}".strip(": "), config)[:200]
        return False, None, f"api_error_{status}: {detail}".rstrip(": ")
    if not isinstance(data, dict):
        return False, None, _unconfirmed("non_object_body")
    messages = data.get("messages")
    if not isinstance(messages, list) or not messages:
        return False, None, _unconfirmed("empty_messages")
    first = messages[0]
    if not isinstance(first, dict):
        return False, None, _unconfirmed("malformed_element")
    message_id = first.get("id")
    if not isinstance(message_id, str) or not message_id.strip():
        return False, None, _unconfirmed("missing_id")
    return True, message_id, None


def _attempt_delivery(store, notification, text, *, env=None, http_post=None, recipient=None):
    """Send `text` for one deliverable notice at most once ever; never raises."""
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
    try:
        ok, message_id, error = send_text_message(config, text() if callable(text) else text, http_post=http_post)
    except Exception as exc:
        row = store.update_whatsapp_attempt(notification["id"], f"unknown:{_scrub(exc, config)[:200]}")
        return {"attempted": True, "state": row["state"], "message_id": row["message_id"]}
    if ok:
        row = store.update_whatsapp_attempt(notification["id"], "accepted_by_api", message_id=message_id)
    elif (error or "").startswith("unconfirmed:"):
        row = store.update_whatsapp_attempt(notification["id"], f"unknown:{error}")
    else:
        row = store.update_whatsapp_attempt(notification["id"], f"failed:{error or 'unknown'}")
    return {"attempted": True, "state": row["state"], "message_id": row["message_id"]}


def attempt_hvac_whatsapp_delivery(store, notification, *, env=None, http_post=None, recipient=None):
    """Attempt real delivery for one HVAC notice; never raises.

    Returns a small status dict. No HTTP happens unless the channel is
    fully opted in, the notice is an allowed hvac_company notice, and no
    attempt was recorded before.
    """
    if not isinstance(notification, dict) or notification.get("audience") != "hvac_company":
        return {"attempted": False, "reason": "not_hvac_notice"}
    return _attempt_delivery(store, notification, lambda: build_hvac_whatsapp_text(notification.get("payload") or {}), env=env, http_post=http_post, recipient=recipient)


def build_caregiver_permission_whatsapp_text(text):
    return "\n".join([WHATSAPP_FIRST_LINE, CAREGIVER_RECIPIENT_NOTE, text])


def attempt_caregiver_permission_whatsapp(store, notification, text, *, env=None, http_post=None, recipient=None):
    """The caregiver permission request: only the caregiver_alert notice, same opt-in and once-only rules as HVAC."""
    if not isinstance(notification, dict) or notification.get("audience") != "family_caregiver" or notification.get("kind") != "caregiver_alert":
        return {"attempted": False, "reason": "not_caregiver_permission"}
    return _attempt_delivery(store, notification, build_caregiver_permission_whatsapp_text(text), env=env, http_post=http_post, recipient=recipient)


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
        "scope": "the hvac_company notice, only after the manager_hvac_authorized or caregiver_hvac_authorized event or an in-app caregiver approval, and the family caregiver's permission request (the caregiver_alert notice); the recipient is always WHATSAPP_TEST_RECIPIENT, which stands in for the HVAC company or the caregiver; any other recipient is refused and nothing is sent",
        "caregiver_permission": {
            "first_lines": [WHATSAPP_FIRST_LINE, CAREGIVER_RECIPIENT_NOTE],
            "content": "the permission question only: room temperature and the time the furnace went quiet, read from evidence visible when the request was raised; no health or personal details",
            "answer": "Approve or Decline in the app; no inbound WhatsApp reply is accepted",
        },
        "opt_in_env": list(REQUIRED_ENV),
        "live_requires": "WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_TEST_RECIPIENT all set plus ARIA_HOME_WHATSAPP_LIVE=1; otherwise the notice stays simulated",
        "simulated_notice": SIMULATED_NOTICE,
        "delivered_notice": DELIVERED_NOTICE,
        "first_line": WHATSAPP_FIRST_LINE,
        "fields_sent": sorted(ALLOWLISTS["hvac_company"]),
        "example_text": build_hvac_whatsapp_text(payload),
        "authorising_event": authorising_event,
        "idempotency": "at most one real send per notification id ever; the attempt is persisted before the API call, so replay, refresh, retry, repeated GETs or a second POST never re-sends; unknown and failed attempts are terminal and never auto-resent",
        "trigger": "explicit POST /api/notifications/<notification_id>/whatsapp only; GET /api/follow-ups/<investigation_id> never sends",
        "status": "GET /api/whatsapp/status reports only whether live delivery is configured, never any value",
        "statuses": ["accepted_by_api", "refused", "unknown:<reason>", "failed:<reason>"],
        "reconciliation": "an 'unknown' state means the API response could not be confirmed: check the owner's test phone manually and do not POST again; there is no resend shortcut",
        "secrets": "credentials only from environment variables; the token is used in-memory for the Authorization header and never lands in the database, responses, logs, attempt rows or ids; the recipient number is never stored",
    }


def _now_iso():
    return datetime.now(timezone.utc).isoformat()
