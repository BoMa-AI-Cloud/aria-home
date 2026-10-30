"""Day 11-06: muse-wonder-1.0 second reviews and muse-voice-transcribe-1.0 human reports."""
import json
from datetime import datetime
from pathlib import Path

from aria_home import review as review_module
from aria_home import transcribe as transcribe_module
from aria_home.app import create_app
from aria_home.investigator import PROMPT_VERSION, build_evidence_pack, inference_identity, investigate
from aria_home.readiness import READINESS_POLICY_VERSION, compute_readiness
from aria_home.review import parse_review, recorded_review_for
from aria_home.scenario import load_scenario
from aria_home.transcribe import human_report_for, parse_transcription_response
from aria_home.verification import verify_recovery
from aria_home.outcomes import follow_up_for

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
VIDEO = "demo_video_v1"
T1631 = "2026-01-16T16:31:00-05:00"
T1821 = "2026-01-16T18:21:00-05:00"
T2101 = "2026-01-16T21:01:00-05:00"
TRANSCRIPT = "The furnace igniter was replaced at seven forty and heat is running."
REVIEW_AT = "2026-01-16T16:31:00-05:00"


def _pack_ids(scenario_id=VIDEO, at_iso=T1631):
    scn = load_scenario(SCENARIOS / scenario_id)
    at = datetime.fromisoformat(at_iso)
    return scn, at, build_evidence_pack(scn, at)["evidence_ids"]


def test_review_valid_no_issues():
    _, _, ids = _pack_ids()
    output = {"verdict": "no_issues", "issues": []}
    parsed, reasons = parse_review(output, ids)
    assert reasons == []
    assert parsed == {"verdict": "no_issues", "issues": []}


def test_review_valid_issues_found():
    _, _, ids = _pack_ids()
    output = {
        "verdict": "issues_found",
        "issues": [
            {"kind": "unsupported_claim", "evidence_ids": ids[:1], "note": "cites a reading that is not current"},
            {"kind": "contradiction", "evidence_ids": ids[:2], "note": "conflicts with the resolved gap"},
            {"kind": "missing_context", "evidence_ids": ids[:1], "note": "omits the stale newest reading"},
            {"kind": "overstated_certainty", "evidence_ids": ids[:1], "note": "states a guess as fact"},
        ],
    }
    parsed, reasons = parse_review(output, ids)
    assert reasons == []
    assert len(parsed["issues"]) == 4


def test_review_unknown_verdict_invalid():
    _, _, ids = _pack_ids()
    parsed, reasons = parse_review({"verdict": "looks_fine", "issues": []}, ids)
    assert parsed is None
    assert any("unknown review verdict" in r for r in reasons)


def test_review_unknown_kind_invalid():
    _, _, ids = _pack_ids()
    output = {"verdict": "issues_found", "issues": [{"kind": "bad_vibes", "evidence_ids": ids[:1], "note": "x"}]}
    parsed, reasons = parse_review(output, ids)
    assert parsed is None
    assert any("unknown kind" in r for r in reasons)


def test_review_foreign_evidence_ids_invalid():
    _, _, ids = _pack_ids()
    output = {"verdict": "issues_found", "issues": [{"kind": "contradiction", "evidence_ids": ["room-temp-9999"], "note": "x"}]}
    parsed, reasons = parse_review(output, ids)
    assert parsed is None
    assert any("outside the pack" in r for r in reasons)


def test_review_overlong_note_invalid():
    _, _, ids = _pack_ids()
    output = {"verdict": "issues_found", "issues": [{"kind": "contradiction", "evidence_ids": ids[:1], "note": "x" * 201}]}
    parsed, reasons = parse_review(output, ids)
    assert parsed is None
    assert any("max 200" in r for r in reasons)
    ok, _ = parse_review({"verdict": "issues_found", "issues": [{"kind": "contradiction", "evidence_ids": ids[:1], "note": "x" * 200}]}, ids)
    assert ok is not None


def test_transcription_response_valid():
    data = {"sessionId": "sess-1", "transcript": TRANSCRIPT, "audioDurationMs": 9000, "turns": [{"text": TRANSCRIPT}]}
    parsed, reasons = parse_transcription_response(data)
    assert reasons == []
    assert parsed["transcript"] == TRANSCRIPT
    assert parsed["session_id"] == "sess-1"


def test_transcription_response_missing_transcript():
    data = {"sessionId": "sess-1", "audioDurationMs": 9000, "turns": []}
    parsed, reasons = parse_transcription_response(data)
    assert parsed is None
    assert any("transcript" in r for r in reasons)


def test_transcription_response_wrong_types():
    for data in (
        {"sessionId": "sess-1", "transcript": TRANSCRIPT, "audioDurationMs": "nine seconds", "turns": []},
        {"sessionId": "sess-1", "transcript": TRANSCRIPT, "audioDurationMs": 9000, "turns": {}},
        {"sessionId": "sess-1", "transcript": "", "audioDurationMs": 9000, "turns": []},
        ["not", "an", "object"],
    ):
        parsed, reasons = parse_transcription_response(data)
        assert parsed is None, data
        assert reasons, data


def _transcript_entries():
    return [{"entry": {"scenario_id": VIDEO, "transcript": TRANSCRIPT, "model_id": "muse-voice-transcribe-1.0", "provider_route": "meta live via Meta Model API (asr/transcribe)", "recorded_at": "2026-10-29T12:00:00+00:00", "audio_fixture": "technician-note-synthetic", "session_id": "sess-1"}, "source": "test"}]


def test_human_report_empty_before_completion_report():
    scn = load_scenario(SCENARIOS / VIDEO)
    assert human_report_for(scn, datetime.fromisoformat("2026-01-16T16:31:00-05:00"), _transcript_entries()) is None


def test_human_report_attached_at_completion_report_time():
    scn = load_scenario(SCENARIOS / VIDEO)
    found = human_report_for(scn, datetime.fromisoformat(T2101), _transcript_entries())
    assert found is not None
    record = found["record"]
    assert record.source.value == "human_report"
    assert record.kind.value == "human_statement"
    assert record.quantity == "technician_note"
    assert record.mode.value == "synthetic"
    assert record.observed_at == datetime.fromisoformat("2026-01-16T20:40:00-05:00")
    assert record.received_at == datetime.fromisoformat("2026-01-16T20:45:00-05:00")
    payload = found["payload"]
    assert payload["transcript"] == TRANSCRIPT
    assert payload["note"] == "human report, not a sensor measurement"
    assert payload["provenance"]["model_id"] == "muse-voice-transcribe-1.0"
    entry = found["timeline_entry"]
    assert entry["kind"] == "human_report"
    assert entry["corroboration_only"] is True
    assert entry["supporting_ids"] == [record.id]


def test_human_report_never_advances_verification():
    scn = load_scenario(SCENARIOS / VIDEO)
    followup = follow_up_for(scn, "inv-hr", datetime.fromisoformat(T1631))
    at = datetime.fromisoformat(T2101)
    before = verify_recovery(scn, followup, at)
    found = human_report_for(scn, at, _transcript_entries())
    assert found is not None
    after = verify_recovery(scn, followup, at)
    assert after["stage"] == before["stage"]
    assert found["record"].id not in after["supporting_ids"]


def test_human_report_never_in_notification_payloads(tmp_path, monkeypatch):
    from aria_home.notifications import build_payload
    from aria_home.scenario import context_as_of, events_as_of

    scn = load_scenario(SCENARIOS / VIDEO)
    at = datetime.fromisoformat(T2101)
    found = human_report_for(scn, at, _transcript_entries())
    assert found is not None
    ctx = context_as_of(scn, at)
    events = events_as_of(scn, at)
    for audience in ("homeowner", "property_manager", "family_caregiver", "hvac_company"):
        payload = build_payload(audience, None, {"status": "cannot_tell", "reasons": ["synthetic"]}, None, ctx, events, at, scn)
        assert TRANSCRIPT not in json.dumps(payload)


def _write_json(directory, name, payload):
    path = Path(directory) / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _recorded_answer(scenario_id=VIDEO, at_iso=T1631):
    scn = load_scenario(SCENARIOS / scenario_id)
    at = datetime.fromisoformat(at_iso)
    identity = inference_identity(scn, at)
    result = investigate(scn, at)
    assert result.status == "ok", result.reasons
    return identity, {
        "scenario_id": scenario_id,
        "evaluated_at_utc": identity["evaluated_at_utc"],
        "input_revision": identity["input_revision"],
        "model_id": "muse-spark-1.3",
        "provider_route": "meta live via Meta Model API",
        "prompt_version": PROMPT_VERSION,
        "readiness_policy_version": READINESS_POLICY_VERSION,
        "code_snapshot": "test-snapshot",
        "recorded_at": "2026-10-28T12:00:00+00:00",
        "output": result.output.model_dump(mode="json"),
    }


def _public_client(tmp_path, monkeypatch, with_review=True, review_output=None):
    for var in ("ARIA_HOME_MODEL_ENABLED", "ARIA_HOME_WHATSAPP_LIVE", "ARIA_HOME_EMPORIA_LIVE", "ARIA_HOME_VISUAL_LIVE", "ARIA_HOME_E2E_HOOKS", "MODEL_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    sessions = tmp_path / "sessions"
    recorded = tmp_path / "recorded"
    reviews = tmp_path / "reviews"
    recorded.mkdir()
    reviews.mkdir()
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(sessions))
    monkeypatch.setenv("ARIA_HOME_RECORDED_DIR", str(recorded))
    monkeypatch.setenv("ARIA_HOME_REVIEWS_DIR", str(reviews))
    identity, answer = _recorded_answer()
    _write_json(recorded, "answers.json", {"answers": [answer]})
    if with_review:
        _, _, ids = _pack_ids()
        output = review_output if review_output is not None else {"verdict": "no_issues", "issues": []}
        _write_json(reviews, "reviews-t1.json", {"reviews": [{
            "scenario_id": VIDEO,
            "evaluated_at_utc": identity["evaluated_at_utc"],
            "input_revision": identity["input_revision"],
            "model_id": "muse-wonder-1.0",
            "review_contract_version": "review-v1",
            "reviewed_model_id": "muse-spark-1.3",
            "provider_route": "meta live via Meta Model API (responses)",
            "recorded_at": "2026-10-29T12:00:00+00:00",
            "review": output,
        }]})
    return create_app().test_client()


def test_recorded_review_shown_beside_matching_answer_ctx(tmp_path, monkeypatch):
    client = _public_client(tmp_path, monkeypatch, with_review=True)
    body = client.post(f"/api/investigations?scenario={VIDEO}&at={REVIEW_AT}").get_json()
    assert body["status"] == "ok"
    shown = body["investigation"]["recorded_review"]
    assert shown["review"] == {"verdict": "no_issues", "issues": []}
    assert shown["provenance"]["model_id"] == "muse-wonder-1.0"
    assert shown["provenance"]["validation"] == {"passed": True, "reasons": []}
    assert shown["provenance"]["reviewed_input_revision"] == body["investigation"]["recorded_provenance"]["input_revision"]


def test_recorded_review_absent_for_other_time(tmp_path, monkeypatch):
    client = _public_client(tmp_path, monkeypatch, with_review=True)
    body = client.get(f"/api/investigation?scenario={VIDEO}&at=2026-01-16T16:52:00-05:00").get_json()
    assert "recorded_review" not in body


def test_recorded_review_absent_without_match(tmp_path, monkeypatch):
    client = _public_client(tmp_path, monkeypatch, with_review=False)
    body = client.post(f"/api/investigations?scenario={VIDEO}&at={REVIEW_AT}").get_json()
    assert body["status"] == "ok"
    assert "recorded_review" not in body["investigation"]


def test_invalid_recorded_review_shown_as_invalid(tmp_path, monkeypatch):
    _, _, ids = _pack_ids()
    bad = {"verdict": "issues_found", "issues": [{"kind": "contradiction", "evidence_ids": ["not-in-pack"], "note": "x"}]}
    client = _public_client(tmp_path, monkeypatch, with_review=True, review_output=bad)
    body = client.post(f"/api/investigations?scenario={VIDEO}&at={REVIEW_AT}").get_json()
    shown = body["investigation"]["recorded_review"]
    assert shown["review"] is None
    assert shown["provenance"]["validation"]["passed"] is False


def test_recorded_review_never_changes_readiness_or_verification(tmp_path, monkeypatch):
    scn = load_scenario(SCENARIOS / VIDEO)
    at = datetime.fromisoformat(REVIEW_AT)
    expected = compute_readiness(build_evidence_pack(scn, at), at)["status"]
    client = _public_client(tmp_path, monkeypatch, with_review=True)
    body = client.post(f"/api/investigations?scenario={VIDEO}&at={REVIEW_AT}").get_json()
    assert body["readiness"]["status"] == expected
    assert body["computed_readiness"] == expected
    followup = follow_up_for(scn, "inv-compare", at)
    direct_stage = verify_recovery(scn, followup, datetime.fromisoformat(T2101))["stage"]
    late = client.get(f"/api/follow-ups/{body['investigation_id']}?at={T2101}").get_json()
    assert late["verification"]["stage"] == direct_stage


def test_follow_up_attaches_human_report_only_after_completion(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    transcripts = tmp_path / "transcripts"
    transcripts.mkdir()
    _write_json(transcripts, "transcripts-t1.json", {"transcripts": [{
        "scenario_id": VIDEO, "transcript": TRANSCRIPT, "model_id": "muse-voice-transcribe-1.0",
        "provider_route": "meta live via Meta Model API (asr/transcribe)",
        "recorded_at": "2026-10-29T12:00:00+00:00", "audio_fixture": "technician-note-synthetic", "session_id": "sess-1",
    }]})
    monkeypatch.setenv("ARIA_HOME_TRANSCRIPTS_DIR", str(transcripts))
    client = create_app().test_client()
    inv_id = client.post(f"/api/investigations?scenario={VIDEO}&at={T1631}").get_json()["investigation_id"]
    early = client.get(f"/api/follow-ups/{inv_id}?at={T1821}").get_json()
    assert "human_report" not in early
    assert "human_report" not in [e["kind"] for e in early["evidence_timeline"]]
    late = client.get(f"/api/follow-ups/{inv_id}?at={T2101}").get_json()
    assert late["human_report"]["transcript"] == TRANSCRIPT
    assert late["human_report"]["note"] == "human report, not a sensor measurement"
    assert late["human_report"]["provenance"]["model_id"] == "muse-voice-transcribe-1.0"
    kinds = [e["kind"] for e in late["evidence_timeline"]]
    assert "human_report" in kinds
    entry = next(e for e in late["evidence_timeline"] if e["kind"] == "human_report")
    assert entry["corroboration_only"] is True
    scn = load_scenario(SCENARIOS / VIDEO)
    followup = follow_up_for(scn, "inv-direct-check", datetime.fromisoformat(T1631))
    assert late["verification"]["stage"] == verify_recovery(scn, followup, datetime.fromisoformat(T2101))["stage"]
    dumped = json.dumps(late["notifications"])
    assert TRANSCRIPT not in dumped


def test_follow_up_verification_identical_without_transcripts(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("ARIA_HOME_TRANSCRIPTS_DIR", str(empty))
    client = create_app().test_client()
    inv_id = client.post(f"/api/investigations?scenario={VIDEO}&at={T1631}").get_json()["investigation_id"]
    body = client.get(f"/api/follow-ups/{inv_id}?at={T2101}").get_json()
    assert "human_report" not in body
    scn = load_scenario(SCENARIOS / VIDEO)
    followup = follow_up_for(scn, "inv-direct", datetime.fromisoformat(T1631))
    assert body["verification"]["stage"] == verify_recovery(scn, followup, datetime.fromisoformat(T2101))["stage"]


def _boom(*args, **kwargs):
    raise AssertionError("live helper must never be called from a route")


def test_no_route_calls_live_helpers(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setattr(review_module, "request_live_review", _boom)
    monkeypatch.setattr(review_module, "send_review_request", _boom)
    monkeypatch.setattr(transcribe_module, "request_live_transcription", _boom)
    monkeypatch.setattr(transcribe_module, "send_transcription_request", _boom)
    client = create_app().test_client()
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/sources?scenario=demo_v1").status_code == 200
    assert client.get("/api/metrics?scenario=demo_v1").status_code == 200
    assert client.get(f"/api/investigation?scenario={VIDEO}&at={T1631}").status_code in (200, 202)
    assert client.get("/api/context?scenario=demo_v1").status_code == 200
    assert client.get("/api/events?scenario=demo_v1").status_code == 200
    assert client.get("/api/visual?scenario=visual_water_low_temp_v1&at=2026-01-16T18:00:00-05:00").status_code == 200
    resp = client.post(f"/api/investigations?scenario={VIDEO}&at={T1631}")
    assert resp.status_code == 200
    inv_id = resp.get_json()["investigation_id"]
    assert client.get(f"/api/follow-ups/{inv_id}?at={T2101}").status_code == 200
    assert client.get(f"/api/notifications?investigation_id={inv_id}").status_code == 200
    assert client.get("/api/provider").status_code == 200
    assert client.get("/api/power-context?scenario=demo_v1").status_code == 200
    assert client.get("/api/live-power").status_code == 200
    assert client.get("/api/whatsapp/status").status_code == 200


def test_public_demo_never_calls_live_helpers(tmp_path, monkeypatch):
    for var in ("ARIA_HOME_MODEL_ENABLED", "ARIA_HOME_WHATSAPP_LIVE", "ARIA_HOME_EMPORIA_LIVE", "ARIA_HOME_VISUAL_LIVE", "ARIA_HOME_E2E_HOOKS"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("ARIA_HOME_RECORDED_DIR", str(tmp_path / "recorded"))
    monkeypatch.setattr(review_module, "request_live_review", _boom)
    monkeypatch.setattr(review_module, "send_review_request", _boom)
    monkeypatch.setattr(transcribe_module, "request_live_transcription", _boom)
    monkeypatch.setattr(transcribe_module, "send_transcription_request", _boom)
    client = create_app().test_client()
    assert client.get("/api/scenarios").status_code == 200
    resp = client.post(f"/api/investigations?scenario={VIDEO}&at={T1631}")
    assert resp.status_code == 200
    inv_id = resp.get_json()["investigation_id"]
    assert client.get(f"/api/follow-ups/{inv_id}?at={T2101}").status_code == 200
    assert client.get("/").status_code in (200, 404)


def test_live_helpers_unreachable_from_app_and_demo_paths():
    root = Path(__file__).resolve().parent.parent / "aria_home"
    for name in ("app.py", "public_demo.py", "recorded.py"):
        text = (root / name).read_text(encoding="utf-8")
        assert "request_live_review" not in text, name
        assert "request_live_transcription" not in text, name
        assert "send_review_request" not in text, name
        assert "send_transcription_request" not in text, name


def test_recorded_review_helper_matches_exact_case_only():
    _, _, ids = _pack_ids()
    scn = load_scenario(SCENARIOS / VIDEO)
    at = datetime.fromisoformat(REVIEW_AT)
    identity = inference_identity(scn, at)
    good = {"entry": {
        "scenario_id": VIDEO, "evaluated_at_utc": identity["evaluated_at_utc"],
        "input_revision": identity["input_revision"], "model_id": "muse-wonder-1.0",
        "review_contract_version": "review-v1", "provider_route": "r",
        "recorded_at": "2026-10-29T12:00:00+00:00",
        "review": {"verdict": "no_issues", "issues": []},
    }, "source": "test"}
    assert recorded_review_for([good], VIDEO, identity["evaluated_at_utc"], identity["input_revision"], ids)["review"] == {"verdict": "no_issues", "issues": []}
    assert recorded_review_for([good], VIDEO, "2026-01-16T21:52:00+00:00", identity["input_revision"], ids) is None
    assert recorded_review_for([good], VIDEO, identity["evaluated_at_utc"], "other-revision", ids) is None
    assert recorded_review_for([good], "demo_v1", identity["evaluated_at_utc"], identity["input_revision"], ids) is None


def test_review_request_uses_max_output_tokens():
    import json as _json

    from aria_home.review import REVIEW_MAX_OUTPUT_TOKENS, REVIEW_URL, build_review_request

    assert REVIEW_MAX_OUTPUT_TOKENS == 16000
    request = build_review_request({"answer": 1}, {"evidence_ids": []})
    assert request["url"] == REVIEW_URL
    assert request["url"].endswith("/v1/responses")
    assert request["body"]["max_output_tokens"] == 16000
    assert "max_tokens" not in request["body"]
    assert "reasoning" not in request["body"]
    _json.dumps(request["body"])


def test_review_response_parses_output_text_blocks():
    import json as _json

    from aria_home.review import parse_review_response

    _, _, ids = _pack_ids()
    review_json = _json.dumps({"verdict": "no_issues", "issues": []})
    data = {"output": [{"content": [{"type": "output_text", "text": review_json}]}]}
    parsed, reasons = parse_review_response(data, ids)
    assert reasons == []
    assert parsed == {"verdict": "no_issues", "issues": []}


def test_review_response_parses_output_text_field():
    import json as _json

    from aria_home.review import parse_review_response

    _, _, ids = _pack_ids()
    data = {"output_text": _json.dumps({"verdict": "no_issues", "issues": []})}
    parsed, reasons = parse_review_response(data, ids)
    assert reasons == []
    assert parsed == {"verdict": "no_issues", "issues": []}


def _incomplete_response():
    return {
        "id": "resp-incomplete",
        "status": "incomplete",
        "incomplete_details": {"reason": "max_output_tokens"},
        "output": [{"type": "reasoning", "id": "rs-1"}],
        "usage": {"output_tokens": 512, "reasoning_tokens": 510},
    }


def _completed_response():
    import json as _json

    return {
        "id": "resp-completed",
        "status": "completed",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": _json.dumps({"verdict": "no_issues", "issues": []})}]}],
        "usage": {"output_tokens": 1770, "reasoning_tokens": 1747},
    }


def test_review_incomplete_response_names_budget_reason():
    from aria_home.review import parse_review_response

    _, _, ids = _pack_ids()
    parsed, reasons = parse_review_response(_incomplete_response(), ids)
    assert parsed is None
    assert reasons == ["review incomplete: max_output_tokens"]


def test_review_incomplete_response_without_details_is_unknown():
    from aria_home.review import parse_review_response

    _, _, ids = _pack_ids()
    parsed, reasons = parse_review_response({"status": "incomplete", "output": []}, ids)
    assert parsed is None
    assert reasons == ["review incomplete: unknown"]


def test_review_failed_response_names_error():
    from aria_home.review import parse_review_response

    _, _, ids = _pack_ids()
    parsed, reasons = parse_review_response({"status": "failed", "error": {"code": "server_error", "message": "boom"}}, ids)
    assert parsed is None
    assert reasons == ["review failed: server_error"]
    parsed, reasons = parse_review_response({"error": {"message": "boom " + "x" * 500}}, ids)
    assert parsed is None
    assert reasons == ["review failed: " + ("boom " + "x" * 500)[:200]]


def test_live_review_reports_incomplete_budget_reason():
    from aria_home.review import build_review_request, request_live_review

    _, _, ids = _pack_ids()
    seen = {}

    def post(url, headers, body, timeout_s):
        seen["body"] = body
        return 200, _incomplete_response()

    result = request_live_review({"answer": 1}, {"evidence_ids": ids}, env={"MODEL_API_KEY": "k"}, http_post=post)
    assert seen["body"]["max_output_tokens"] == 16000
    assert "reasoning" not in seen["body"]
    assert result["ok"] is True
    assert result["review"] is None
    assert result["validation"] == {"passed": False, "reasons": ["review incomplete: max_output_tokens"]}


def test_live_review_completed_shape_passes_no_issues():
    from aria_home.review import request_live_review

    _, _, ids = _pack_ids()
    seen = {}

    def post(url, headers, body, timeout_s):
        seen["body"] = body
        return 200, _completed_response()

    result = request_live_review({"answer": 1}, {"evidence_ids": ids}, env={"MODEL_API_KEY": "k"}, http_post=post)
    assert seen["body"]["max_output_tokens"] == 16000
    assert result["ok"] is True
    assert result["review"] == {"verdict": "no_issues", "issues": []}
    assert result["validation"] == {"passed": True, "reasons": []}
