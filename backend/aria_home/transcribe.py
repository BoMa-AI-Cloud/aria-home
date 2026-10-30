"""muse-voice-transcribe-1.0 transcription of a synthetic technician voice note.

The recorded transcript becomes a human-report record (source kind
human_report): corroboration only, never a measurement, outcome, or
verification input, and its text never enters HVAC or WhatsApp payloads.
The UI shows the transcript with its provenance and the label "human
report, not a sensor measurement".

The live request below is implemented for an ASR-compatible API
(POST https://api.meta.ai/v1/asr/transcribe, header "Authorization: Bearer
<key>", multipart parts `request` (application/json with model,
audioEncoding, mode) and `audio` (WAV bytes)). The response shape is NOT
verified against the API reference, which was not checked. The live helper
is operator-only: no route, no GET handler, and no public-demo path may
call it. Recorded transcripts live in backend/eval/transcripts-*.json.
"""

import json
import math
import os
from pathlib import Path

import httpx

from .contracts import DataMode, EvidenceKind, EvidenceRecord, Provenance, SourceKind
from .verification import REPORT_EVENT_KIND

TRANSCRIBE_MODEL_ID = "muse-voice-transcribe-1.0"
TRANSCRIBE_ALLOWED_MODEL_IDS = frozenset({TRANSCRIBE_MODEL_ID})
TRANSCRIBE_URL = "https://api.meta.ai/v1/asr/transcribe"
TRANSCRIBE_PROVIDER_ROUTE = "meta live via Meta Model API (asr/transcribe)"
DEFAULT_TIMEOUT_S = 20.0
TRANSCRIPTS_DIR_ENV = "ARIA_HOME_TRANSCRIPTS_DIR"
AUDIO_ENCODING = "WAV"
TRANSCRIBE_MODE = "PUSH_TO_TALK"
AUDIO_FIXTURE_ID = "technician-note-synthetic"
REPORT_QUANTITY = "technician_note"
REPORT_ZONE = "demo-house/main"
SOURCE_NOTE = "transcribed by muse-voice-transcribe-1.0 from a synthetic voice note"
HUMAN_REPORT_LABEL = "human report, not a sensor measurement"
REPORT_RECORD_ID = "human-report:technician-note-synthetic"


def transcripts_dir(env=None):
    source = os.environ if env is None else env
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    raw = get(TRANSCRIPTS_DIR_ENV)
    if raw:
        return Path(raw).expanduser()
    return Path(__file__).resolve().parent.parent / "eval"


def parse_transcription_response(data):
    """Validate an ASR response shape.

    Returns (transcript, reasons): transcript is the normalized
    {"session_id", "transcript", "audio_duration_ms", "turns"} dict when
    valid, else None. A missing or mistyped field fails.
    """
    if not isinstance(data, dict):
        return None, ["transcription response must be a JSON object"]
    reasons = []
    session_id = data.get("sessionId")
    if not isinstance(session_id, str) or not session_id:
        reasons.append("transcription response needs a non-empty string sessionId")
    transcript = data.get("transcript")
    if not isinstance(transcript, str) or not transcript:
        reasons.append("transcription response needs a non-empty string transcript")
    duration = data.get("audioDurationMs")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration):
        reasons.append("transcription response needs a numeric audioDurationMs")
    turns = data.get("turns")
    if not isinstance(turns, list):
        reasons.append("transcription response needs a list of turns")
    if reasons:
        return None, reasons
    return {
        "session_id": session_id,
        "transcript": transcript,
        "audio_duration_ms": duration,
        "turns": list(turns),
    }, []


def build_transcribe_request(wav_bytes, filename="technician-note-synthetic.wav"):
    return {
        "url": TRANSCRIBE_URL,
        "request_part": {
            "model": TRANSCRIBE_MODEL_ID,
            "audioEncoding": AUDIO_ENCODING,
            "mode": TRANSCRIBE_MODE,
        },
        "audio_part": {
            "filename": filename,
            "content": bytes(wav_bytes),
            "content_type": "audio/wav",
        },
    }


def _default_http_post(url, headers, request_part, audio_part, timeout_s):
    files = {
        "request": (None, json.dumps(request_part), "application/json"),
        "audio": (audio_part["filename"], audio_part["content"], audio_part["content_type"]),
    }
    with httpx.Client(timeout=timeout_s) as client:
        response = client.post(url, headers=headers, files=files)
    try:
        data = response.json()
    except ValueError:
        data = None
    return response.status_code, data


def send_transcription_request(api_key, wav_bytes, *, filename="technician-note-synthetic.wav", timeout_s=DEFAULT_TIMEOUT_S, http_post=None):
    """Single multipart POST with no retry, mirroring the provider's handling."""
    post = http_post or _default_http_post
    request = build_transcribe_request(wav_bytes, filename=filename)
    try:
        status, data = post(
            request["url"],
            {"Authorization": f"Bearer {api_key}"},
            request["request_part"],
            request["audio_part"],
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
    if not isinstance(data, dict):
        return {"ok": False, "error": "bad_response"}
    return {"ok": True, "status": status, "data": data}


def request_live_transcription(wav_path, *, env=None, http_post=None, timeout_s=DEFAULT_TIMEOUT_S):
    """Operator-only live transcription. Never called from routes or public-demo code."""
    source = os.environ if env is None else env
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    api_key = get("MODEL_API_KEY")
    if isinstance(api_key, str):
        api_key = api_key.strip() or None
    if not api_key:
        return {"ok": False, "error": "not_configured", "transcript": None, "validation": {"passed": False, "reasons": ["MODEL_API_KEY is not set"]}}
    try:
        wav_bytes = Path(wav_path).read_bytes()
    except OSError as exc:
        return {"ok": False, "error": "bad_audio", "transcript": None, "validation": {"passed": False, "reasons": [f"cannot read audio fixture: {exc}"]}}
    sent = send_transcription_request(api_key, wav_bytes, filename=Path(wav_path).name, timeout_s=timeout_s, http_post=http_post)
    if not sent.get("ok"):
        return {"ok": False, "error": sent.get("error"), "transcript": None, "validation": {"passed": False, "reasons": [f"transcription request failed: {sent.get('error')}"]}}
    transcript, reasons = parse_transcription_response(sent.get("data"))
    return {
        "ok": True,
        "error": None,
        "transcript": transcript,
        "raw_response": sent.get("data"),
        "validation": {"passed": not reasons, "reasons": list(reasons)},
    }


def _transcript_entries(payload, source):
    if isinstance(payload, dict) and isinstance(payload.get("transcripts"), list):
        items = payload["transcripts"]
    elif isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("transcript"), str):
        items = [payload]
    else:
        return
    for item in items:
        if isinstance(item, dict):
            yield {"entry": item, "source": source}


def load_recorded_transcripts(directory=None):
    directory = Path(directory) if directory is not None else transcripts_dir()
    entries = []
    if directory.is_dir():
        for path in sorted(directory.glob("transcripts-*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            entries.extend(_transcript_entries(payload, str(path)))
    return entries


def find_recorded_transcript(entries, scenario_id):
    for item in entries:
        entry = item.get("entry")
        if not isinstance(entry, dict):
            continue
        if (
            entry.get("scenario_id") == scenario_id
            and isinstance(entry.get("transcript"), str)
            and entry["transcript"]
            and entry.get("model_id", TRANSCRIBE_MODEL_ID) in TRANSCRIBE_ALLOWED_MODEL_IDS
        ):
            return item
    return None


def _completion_report(scenario, now):
    candidates = [
        event
        for event in (getattr(scenario, "events", None) or [])
        if getattr(event, "kind", None) == REPORT_EVENT_KIND and getattr(event, "available_at", None) <= now
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda e: (e.available_at, e.event_time, e.id))[-1]


def human_report_record(entry, *, observed_at, received_at, zone=REPORT_ZONE):
    return EvidenceRecord(
        id=REPORT_RECORD_ID,
        source=SourceKind.human_report,
        kind=EvidenceKind.human_statement,
        subject=zone,
        quantity=REPORT_QUANTITY,
        value=entry.get("transcript"),
        unit=None,
        observed_at=observed_at,
        received_at=received_at,
        expected_cadence_s=None,
        mode=DataMode.synthetic,
        provenance=Provenance(fixture_id=AUDIO_FIXTURE_ID, version="1"),
    )


def transcript_records_for(scenario, entries, now):
    """Build the human-report record once the completion report is known.

    Returns (records, entry): at most one record, attached at the existing
    completion-report time (observed at the report's event time, received
    when the report became available). Empty before that time.
    """
    report = _completion_report(scenario, now)
    if report is None:
        return [], None
    if entries is None:
        entries = load_recorded_transcripts()
    match = find_recorded_transcript(entries, scenario.manifest.id)
    if match is None:
        return [], None
    record = human_report_record(match["entry"], observed_at=report.event_time, received_at=report.available_at)
    return [record], match["entry"]


def human_report_payload(record, entry):
    return {
        "record_id": record.id,
        "source": SourceKind.human_report.value,
        "transcript": record.value,
        "observed_at": record.observed_at.isoformat(),
        "received_at": record.received_at.isoformat(),
        "zone": record.subject,
        "provenance": {
            "model_id": entry.get("model_id", TRANSCRIBE_MODEL_ID),
            "provider_route": entry.get("provider_route") or TRANSCRIBE_PROVIDER_ROUTE,
            "recorded_at": entry.get("recorded_at"),
            "audio_fixture": entry.get("audio_fixture", AUDIO_FIXTURE_ID),
            "session_id": entry.get("session_id"),
            "source_note": SOURCE_NOTE,
        },
        "note": HUMAN_REPORT_LABEL,
    }


def human_report_timeline_entry(record):
    return {
        "kind": "human_report",
        "label": "Technician voice-note report available",
        "supporting_ids": [record.id],
        "supporting_record_ids": [record.id],
        "observed_at": record.observed_at,
        "received_at": record.received_at,
        "available_at": record.received_at,
        "first_known_at": record.received_at,
        "evaluated_at": record.received_at,
        "corroboration_only": True,
    }


def human_report_for(scenario, now, entries=None):
    """Full human-report attachment for a follow-up response, or None."""
    records, entry = transcript_records_for(scenario, entries, now)
    if not records or entry is None:
        return None
    record = records[0]
    return {
        "record": record,
        "entry": entry,
        "payload": human_report_payload(record, entry),
        "timeline_entry": human_report_timeline_entry(record),
    }


__all__ = [
    "AUDIO_ENCODING",
    "AUDIO_FIXTURE_ID",
    "DEFAULT_TIMEOUT_S",
    "HUMAN_REPORT_LABEL",
    "REPORT_QUANTITY",
    "REPORT_RECORD_ID",
    "REPORT_ZONE",
    "SOURCE_NOTE",
    "TRANSCRIBE_ALLOWED_MODEL_IDS",
    "TRANSCRIBE_MODE",
    "TRANSCRIBE_MODEL_ID",
    "TRANSCRIBE_PROVIDER_ROUTE",
    "TRANSCRIBE_URL",
    "build_transcribe_request",
    "find_recorded_transcript",
    "human_report_for",
    "human_report_payload",
    "human_report_record",
    "human_report_timeline_entry",
    "load_recorded_transcripts",
    "parse_transcription_response",
    "request_live_transcription",
    "send_transcription_request",
    "transcript_records_for",
    "transcripts_dir",
]
