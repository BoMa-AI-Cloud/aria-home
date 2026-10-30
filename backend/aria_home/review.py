"""muse-wonder-1.0 structured second review of a recorded explanation.

A review reads a recorded muse-spark-1.3 answer that already passed
validation, plus the evidence pack that answer was checked against, and
returns a JSON verdict: {"verdict": "no_issues" | "issues_found", "issues":
[{"kind", "evidence_ids", "note"}]}. Issues may only cite evidence ids from
that pack, and notes are capped at 200 characters.

A review never changes readiness, verification, permissions, or validity,
and "no_issues" is not verification. Only a recorded review whose case
(scenario id, evaluated time, input revision) matches the displayed answer
is ever shown, and only beside that answer.

The live request below is implemented for a Responses-compatible API
(POST https://api.meta.ai/v1/responses, header "Authorization: Bearer
<key>"). The request body shape is NOT verified against the API reference,
which was not checked. The live helper is operator-only: no route, no GET
handler, and no public-demo path may call it. Recorded reviews live in
backend/eval/reviews-*.json and are matched exactly like recorded answers.
"""

import glob
import json
import os
from pathlib import Path

import httpx

REVIEW_MODEL_ID = "muse-wonder-1.0"
REVIEW_ALLOWED_MODEL_IDS = frozenset({REVIEW_MODEL_ID})
REVIEW_CONTRACT_VERSION = "review-v1"
REVIEW_BASE_URL = "https://api.meta.ai"
REVIEW_PATH = "/v1/responses"
REVIEW_URL = REVIEW_BASE_URL + REVIEW_PATH
REVIEW_PROVIDER_ROUTE = "meta live via Meta Model API (responses)"
DEFAULT_TIMEOUT_S = 20.0
DEFAULT_MAX_TOKENS = 512
MAX_NOTE_CHARS = 200
REVIEW_VERDICTS = ("no_issues", "issues_found")
REVIEW_ISSUE_KINDS = (
    "unsupported_claim",
    "contradiction",
    "missing_context",
    "overstated_certainty",
)
REVIEWS_DIR_ENV = "ARIA_HOME_REVIEWS_DIR"

REVIEW_SYSTEM_PROMPT = """You are a second reviewer for a home-monitoring assistant. \
You receive one validated model answer and the evidence pack it was checked against. \
Do not re-investigate the home and do not change any status. Reply with JSON only: \
{"verdict": "no_issues" | "issues_found", "issues": [{"kind": \
"unsupported_claim" | "contradiction" | "missing_context" | "overstated_certainty", \
"evidence_ids": ["<ids from the pack only>"], "note": "<at most 200 characters>"}]}. \
A "no_issues" verdict is not verification of the home; it only means you found no \
issue in the answer. Cite evidence references and concise conclusions only."""


def reviews_dir(env=None):
    source = os.environ if env is None else env
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    raw = get(REVIEWS_DIR_ENV)
    if raw:
        return Path(raw).expanduser()
    return Path(__file__).resolve().parent.parent / "eval"


def _norm_time(value):
    from datetime import datetime, timezone

    return (
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        .astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def parse_review(output, evidence_ids):
    """Strictly validate a review output dict against pack evidence ids.

    Returns (review, reasons): review is the normalized {"verdict", "issues"}
    dict when valid, else None. Unknown verdicts or issue kinds, evidence ids
    outside the pack, and notes over 200 characters all fail.
    """
    valid_ids = set(evidence_ids or [])
    if not isinstance(output, dict):
        return None, ["review output must be a JSON object"]
    reasons = []
    verdict = output.get("verdict")
    if verdict not in REVIEW_VERDICTS:
        reasons.append(f"unknown review verdict: {verdict!r}")
    issues = output.get("issues")
    if not isinstance(issues, list):
        reasons.append("review issues must be a list")
        issues = None
    normalized = []
    if issues is not None:
        for index, issue in enumerate(issues):
            where = f"review issue {index}"
            if not isinstance(issue, dict):
                reasons.append(f"{where} must be an object")
                continue
            kind = issue.get("kind")
            if kind not in REVIEW_ISSUE_KINDS:
                reasons.append(f"{where} has unknown kind: {kind!r}")
                continue
            ids = issue.get("evidence_ids")
            if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids):
                reasons.append(f"{where} evidence_ids must be a list of strings")
                continue
            foreign = [i for i in ids if i not in valid_ids]
            if foreign:
                reasons.append(f"{where} cites evidence outside the pack: {sorted(foreign)}")
                continue
            note = issue.get("note")
            if not isinstance(note, str):
                reasons.append(f"{where} note must be a string")
                continue
            if len(note) > MAX_NOTE_CHARS:
                reasons.append(f"{where} note is {len(note)} characters (max {MAX_NOTE_CHARS})")
                continue
            normalized.append({"kind": kind, "evidence_ids": list(ids), "note": note})
    if reasons:
        return None, reasons
    return {"verdict": verdict, "issues": normalized}, []


def _candidate_texts(data):
    if isinstance(data, str):
        yield data
        return
    if not isinstance(data, dict):
        return
    if isinstance(data.get("verdict"), str):
        yield json.dumps(data)
        return
    text = data.get("text")
    if isinstance(text, str):
        yield text
    output = data.get("output")
    if isinstance(output, list):
        parts = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, list):
                parts.extend(
                    block.get("text")
                    for block in content
                    if isinstance(block, dict) and isinstance(block.get("text"), str)
                )
            elif isinstance(content, str):
                parts.append(content)
        if parts:
            yield "".join(parts)


def parse_review_response(data, evidence_ids):
    """Extract a review output from a Responses-API envelope, then validate."""
    for candidate in _candidate_texts(data):
        try:
            output = json.loads(candidate)
        except ValueError:
            continue
        return parse_review(output, evidence_ids)
    return None, ["review response carried no JSON review output"]


def build_review_request(answer_output, evidence_pack, model_id=REVIEW_MODEL_ID):
    if model_id not in REVIEW_ALLOWED_MODEL_IDS:
        raise ValueError(
            f"disallowed review model id: {model_id!r}; "
            f"allowed model ids: {sorted(REVIEW_ALLOWED_MODEL_IDS)}"
        )
    user_content = json.dumps(
        {
            "reviewed_answer": answer_output,
            "evidence_pack": evidence_pack,
            "review_contract_version": REVIEW_CONTRACT_VERSION,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return {
        "url": REVIEW_URL,
        "body": {
            "model": model_id,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "input": [
                {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        },
    }


def _default_http_post(url, headers, body, timeout_s):
    with httpx.Client(timeout=timeout_s) as client:
        response = client.post(url, headers=headers, json=body)
    try:
        data = response.json()
    except ValueError:
        data = None
    return response.status_code, data


def send_review_request(request, api_key, timeout_s=DEFAULT_TIMEOUT_S, http_post=None):
    """Single POST with no retry, mirroring the existing provider's handling."""
    post = http_post or _default_http_post
    try:
        status, data = post(
            request["url"],
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            request["body"],
            timeout_s,
        )
    except httpx.TimeoutException:
        return {"ok": False, "error": "timeout"}
    except httpx.HTTPError:
        return {"ok": False, "error": "server_error"}
    if status in (401, 403):
        return {"ok": False, "error": "auth"}
    if status == 429:
        return {"ok": False, "error": "rate_limited"}
    if status is None or not 200 <= status <= 299:
        return {"ok": False, "error": "bad_response"}
    if not isinstance(data, (dict, str)):
        return {"ok": False, "error": "bad_response"}
    return {"ok": True, "status": status, "data": data}


def request_live_review(answer_output, evidence_pack, *, env=None, http_post=None, timeout_s=DEFAULT_TIMEOUT_S, model_id=REVIEW_MODEL_ID):
    """Operator-only live review. Never called from routes or public-demo code."""
    source = os.environ if env is None else env
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    api_key = get("MODEL_API_KEY")
    if isinstance(api_key, str):
        api_key = api_key.strip() or None
    if not api_key:
        return {"ok": False, "error": "not_configured", "review": None, "validation": {"passed": False, "reasons": ["MODEL_API_KEY is not set"]}}
    try:
        request = build_review_request(answer_output, evidence_pack, model_id=model_id)
    except ValueError as exc:
        return {"ok": False, "error": "model_mismatch", "review": None, "validation": {"passed": False, "reasons": [str(exc)]}}
    sent = send_review_request(request, api_key, timeout_s=timeout_s, http_post=http_post)
    if not sent.get("ok"):
        return {"ok": False, "error": sent.get("error"), "review": None, "validation": {"passed": False, "reasons": [f"review request failed: {sent.get('error')}"]}}
    review, reasons = parse_review_response(sent.get("data"), (evidence_pack or {}).get("evidence_ids") or [])
    return {
        "ok": True,
        "error": None,
        "review": review,
        "raw_output": sent.get("data"),
        "validation": {"passed": not reasons, "reasons": list(reasons)},
    }


def _review_entries(payload, source):
    if isinstance(payload, dict) and isinstance(payload.get("reviews"), list):
        items = payload["reviews"]
    elif isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("review"), dict):
        items = [payload]
    else:
        return
    for item in items:
        if isinstance(item, dict):
            yield {"entry": item, "source": source}


def load_recorded_reviews(directory=None):
    directory = Path(directory) if directory is not None else reviews_dir()
    entries = []
    if directory.is_dir():
        for path in sorted(directory.glob("reviews-*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            entries.extend(_review_entries(payload, str(path)))
    return entries


def find_recorded_review(entries, scenario_id, evaluated_at_utc, input_revision):
    try:
        wanted_at = _norm_time(evaluated_at_utc)
    except (TypeError, ValueError):
        return None
    for item in entries:
        entry = item.get("entry")
        if not isinstance(entry, dict):
            continue
        try:
            entry_at = _norm_time(entry.get("evaluated_at_utc"))
        except (TypeError, ValueError):
            continue
        if (
            entry.get("scenario_id") == scenario_id
            and entry_at == wanted_at
            and entry.get("input_revision") == input_revision
            and entry.get("model_id", REVIEW_MODEL_ID) in REVIEW_ALLOWED_MODEL_IDS
            and entry.get("review_contract_version", REVIEW_CONTRACT_VERSION) == REVIEW_CONTRACT_VERSION
        ):
            return item
    return None


def review_provenance(entry, validation_reasons):
    return {
        "model_id": entry.get("model_id", REVIEW_MODEL_ID),
        "provider_route": entry.get("provider_route") or REVIEW_PROVIDER_ROUTE,
        "recorded_at": entry.get("recorded_at"),
        "review_contract_version": entry.get("review_contract_version", REVIEW_CONTRACT_VERSION),
        "reviewed_model_id": entry.get("reviewed_model_id"),
        "reviewed_input_revision": entry.get("input_revision"),
        "reviewed_at": entry.get("evaluated_at_utc"),
        "validation": {"passed": not validation_reasons, "reasons": list(validation_reasons)},
    }


def recorded_review_for(entries, scenario_id, evaluated_at_utc, input_revision, evidence_ids):
    """Return the recorded review for a displayed answer, or None.

    The review output is re-validated against the current evidence pack. An
    invalid recording is kept and returned with its reasons so the UI can
    show it as invalid; it still changes nothing.
    """
    match = find_recorded_review(entries, scenario_id, evaluated_at_utc, input_revision)
    if match is None:
        return None
    entry = match["entry"]
    review, reasons = parse_review(entry.get("review"), evidence_ids)
    if review is not None:
        from .laws import check_output as _check_laws

        for violation in _check_laws(review, {"evidence": [{"id": i} for i in (evidence_ids or [])]}):
            reasons.append(f"law {violation['law']}: {violation['reason']}")
        if reasons:
            review = None
    return {
        "review": review,
        "raw_output": entry.get("review"),
        "provenance": review_provenance(entry, reasons),
    }


__all__ = [
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_TIMEOUT_S",
    "MAX_NOTE_CHARS",
    "REVIEW_ALLOWED_MODEL_IDS",
    "REVIEW_CONTRACT_VERSION",
    "REVIEW_ISSUE_KINDS",
    "REVIEW_MODEL_ID",
    "REVIEW_PROVIDER_ROUTE",
    "REVIEW_SYSTEM_PROMPT",
    "REVIEW_URL",
    "REVIEW_VERDICTS",
    "build_review_request",
    "find_recorded_review",
    "load_recorded_reviews",
    "parse_review",
    "parse_review_response",
    "recorded_review_for",
    "request_live_review",
    "review_provenance",
    "reviews_dir",
    "send_review_request",
]
