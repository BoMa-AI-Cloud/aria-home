"""ARIA's view trace: matches the decision functions, as-of only, zero model calls."""
from datetime import datetime

import pytest

from aria_home import laws as laws_module
from aria_home.app import create_app
from aria_home.contracts import SourceKind
from aria_home.eligibility import unresolved_conflict_groups
from aria_home.evidence import source_status
from aria_home.investigator import PROMPT_VERSION, build_evidence_pack, inference_identity
from aria_home.notifications import decide_hvac_notification, decide_notifications
from aria_home.outcomes import follow_up_for
from aria_home import public_demo
from aria_home.readiness import READINESS_POLICY_VERSION
from aria_home.recorded import public_investigation
from aria_home.scenario import context_as_of, events_as_of, load_scenario, visible_records
from aria_home.trace import build_trace
from aria_home.transcribe import HUMAN_REPORT_LABEL, human_report_for
from aria_home.verification import build_evidence_timeline, verify_recovery
from aria_home.watcher import public_watcher

SCENARIO_PATH = "scenarios/care_home_v1"
CHECKPOINTS = list(public_demo.CHECKPOINTS["care_home_v1"])
AT_0231 = "2026-01-17T02:31:00-05:00"


@pytest.fixture(scope="module")
def scn():
    from pathlib import Path

    return load_scenario(Path(__file__).resolve().parent.parent / SCENARIO_PATH)


def _at(iso):
    return datetime.fromisoformat(iso)


def _followup_or_none(scn, at):
    identity = inference_identity(scn, at)
    try:
        return follow_up_for(scn, identity["investigation_id"], at), None
    except ValueError as exc:
        return None, str(exc)


def test_trace_matches_sources_and_readiness_at_every_checkpoint(scn):
    assert len(CHECKPOINTS) == 10
    for iso in CHECKPOINTS:
        at = _at(iso)
        pack = build_evidence_pack(scn, at)
        trace = build_trace(scn, at)
        assert trace["scenario"] == "care_home_v1"
        assert trace["at"] == at.isoformat()
        assert trace["input_revision"] == inference_identity(scn, at)["input_revision"]
        expected_sources = [s["source"] if isinstance(s, dict) else s.source.value for s in pack["source_statuses"]]
        assert [s["source"] for s in trace["sources"]] == expected_sources
        visible = visible_records(scn.records, at)
        for status in pack["source_statuses"]:
            name = status["source"] if isinstance(status, dict) else status.source.value
            direct = source_status(SourceKind(name), visible, at, mode=scn.manifest.mode)
            row = next(s for s in trace["sources"] if s["source"] == name)
            assert row["availability"] == direct.availability.value
            assert row["record_count"] == direct.record_count
        assert trace["readiness"]["status"] == pack["readiness"]["status"]
        assert trace["readiness"]["reasons"] == list(pack["readiness"]["reasons"])
        assert [step["seq"] for step in trace["steps"]] == list(range(len(trace["steps"])))


def test_trace_matches_verification_and_timeline(scn):
    for iso in CHECKPOINTS:
        at = _at(iso)
        trace = build_trace(scn, at)
        followup, reason = _followup_or_none(scn, at)
        verification = trace["verification"]
        if followup is None:
            assert verification["available"] is False
            assert reason in verification["reason"]
            assert trace["verification_timeline"] == []
        else:
            direct = verify_recovery(scn, followup, at)
            assert verification["available"] is True
            assert verification["stage"] == direct["stage"]
            assert verification["reasons"] == list(direct["reasons"])
            assert verification["supporting_ids"] == list(direct["supporting_ids"])
            expected_timeline = build_evidence_timeline(scn, followup, at)
            assert [e["label"] for e in trace["verification_timeline"]] == [e["label"] for e in expected_timeline]
            assert len(trace["verification_timeline"]) == len(expected_timeline)


def test_trace_matches_watcher_human_and_notices(scn):
    for iso in CHECKPOINTS:
        at = _at(iso)
        trace = build_trace(scn, at)
        assert trace["watcher_summary"] == public_watcher(scn, at)
        human = human_report_for(scn, at)
        if human is None:
            assert trace["human_report"] is None
        else:
            assert trace["human_report"]["payload"] == human_report_for(scn, at)["payload"]
            assert trace["human_report"]["label"] == HUMAN_REPORT_LABEL
            assert "not a sensor measurement" in trace["human_report"]["label"]
        investigation, _ = public_investigation(scn, at)
        pack = build_evidence_pack(scn, at)
        verification = trace["verification"]
        verification_for_notif = {k: v for k, v in verification.items() if k != "available"} if verification.get("available") else None
        expected = decide_notifications(investigation, pack["readiness"], verification_for_notif, context_as_of(scn, at), events_as_of(scn, at), at, scn, inference_identity(scn, at)["investigation_id"])
        expected = list(expected) + [decide_hvac_notification(investigation, pack["readiness"], verification_for_notif, context_as_of(scn, at), events_as_of(scn, at), at, scn, inference_identity(scn, at)["investigation_id"])]
        assert [(n["audience"], n["allowed"], n["reason"]) for n in trace["notices"]] == [(d["audience"], d["allowed"], d.get("reason")) for d in expected]
        assert any("human report, not a measurement" in step["label"] or step["kind"] != "human" for step in trace["steps"])
        if human is not None:
            assert any(step["kind"] == "human" and "not a measurement" in step["label"] for step in trace["steps"])


def test_trace_shows_no_future_evidence(scn):
    from datetime import timedelta

    for iso in CHECKPOINTS:
        at = _at(iso)
        trace = build_trace(scn, at)
        pack = build_evidence_pack(scn, at)
        by_id = {item["id"]: item for item in pack.get("evidence", []) if isinstance(item, dict)}
        cited = set()
        for source in trace["sources"]:
            if source["latest_reading"] is not None:
                cited.add(source["latest_reading"]["id"])
        for obs in trace["watcher"]["observations"]:
            cited.update(obs.get("evidence_ids") or [])
        verification = trace["verification"]
        cited.update(verification.get("supporting_ids") or [])
        for entry in trace["verification_timeline"]:
            cited.update(entry.get("supporting_ids") or [])
        for rid in cited:
            item = by_id.get(rid)
            if item is None or "quantity" not in item:
                continue
            received = datetime.fromisoformat(str(item["received_at"]).replace("Z", "+00:00"))
            observed = datetime.fromisoformat(str(item["observed_at"]).replace("Z", "+00:00"))
            assert received <= at, f"{rid} received after the replay time"
            assert observed <= at + timedelta(seconds=60), f"{rid} observed after the replay time"


def test_trace_failed_checks_carry_reasons(scn):
    at = _at(AT_0231)
    trace = build_trace(scn, at)
    stale = [c for c in trace["checks"] if c["check"] == "freshness" and c["target"] == "thermostat"]
    assert stale and all(c["passed"] is False and c["reason"] for c in stale)
    failed_anywhere = [c for iso in CHECKPOINTS for c in build_trace(scn, _at(iso))["checks"] if c["passed"] is False]
    assert failed_anywhere and all(c["reason"] for c in failed_anywhere)
    law_ids = {law["id"] for law in laws_module.active_model_laws()}
    traced_laws = {c["check"].split("law:", 1)[1] for c in trace["checks"] if c["check"].startswith("law:")}
    assert law_ids and law_ids <= traced_laws


def test_trace_law_violation_names_the_law(scn):
    at = _at(AT_0231)
    identity = inference_identity(scn, at)
    target_law = next(law for law in laws_module.active_model_laws() if law.get("check") == "check_no_detection_not_safe")
    answer = {
        "scenario_id": identity["scenario_id"],
        "evaluated_at_utc": identity["evaluated_at_utc"],
        "input_revision": identity["input_revision"],
        "model_id": "muse-spark-1.3",
        "provider_route": "test",
        "prompt_version": PROMPT_VERSION,
        "readiness_policy_version": READINESS_POLICY_VERSION,
        "code_snapshot": "test",
        "recorded_at": "2026-10-29T00:00:00Z",
        "output": {"interpretation": "All clear here, definitely safe.", "hypotheses": [], "unknowns": [], "clarification": "none", "follow_up": {"observation": "none"}, "readiness": "cannot_tell", "limitations": []},
    }
    trace = build_trace(scn, at, entries=[{"answer": answer, "source": "test"}])
    rows = [c for c in trace["checks"] if c["check"] == f"law:{target_law['id']}" and c["target"] == "investigation"]
    assert rows and all(r["passed"] is False and r["reason"] for r in rows)
    assert any(target_law["id"] in step["detail"] or target_law["id"] in step["label"] for step in trace["steps"] if step["kind"] == "check")


def test_trace_makes_zero_model_calls(scn, monkeypatch):
    import httpx

    import aria_home.investigator as investigator_module

    def _forbidden(*args, **kwargs):
        raise AssertionError("trace must never call a model")

    monkeypatch.setattr(investigator_module, "get_provider", _forbidden)
    monkeypatch.setattr(httpx, "Client", _forbidden)
    for iso in CHECKPOINTS:
        trace = build_trace(scn, _at(iso))
        assert trace["computed_by"] == "deterministic code"
        assert trace["steps"]


def test_trace_endpoint_is_read_only_json():
    client = create_app().test_client()
    resp = client.get(f"/api/trace?scenario=care_home_v1&at={AT_0231}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["data_mode"] == "synthetic"
    assert body["recorded_only"] is True
    assert body["steps"] and [s["seq"] for s in body["steps"]] == list(range(len(body["steps"])))
    assert client.post(f"/api/trace?scenario=care_home_v1&at={AT_0231}").status_code == 405
    assert client.get("/api/trace?scenario=care_home_v1&at=not-a-time").status_code == 400
    assert client.get("/api/trace?scenario=nope&at=2026-01-17T02:31:00-05:00").status_code == 404


def test_trace_public_demo_allows_only_checkpoints(monkeypatch, tmp_path):
    for var in ("ARIA_HOME_MODEL_ENABLED", "ARIA_HOME_E2E_HOOKS", "ARIA_HOME_DB_PATH"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    sessions = tmp_path / "sessions"
    recorded = tmp_path / "recorded"
    recorded.mkdir()
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(sessions))
    monkeypatch.setenv("ARIA_HOME_RECORDED_DIR", str(recorded))
    client = create_app().test_client()
    ok = client.get(f"/api/trace?scenario=care_home_v1&at={AT_0231}")
    assert ok.status_code == 200
    assert ok.get_json()["steps"]
    bad = client.get("/api/trace?scenario=care_home_v1&at=2026-01-17T03:00:00-05:00")
    assert bad.status_code == 400


def test_permission_step_follows_the_caregiver_and_never_shows_the_future(scn):
    assert build_trace(scn, _at("2026-01-16T19:15:00-05:00"))["permission"] is None
    waiting = build_trace(scn, _at(AT_0231))
    assert waiting["permission"]["status"] == "waiting"
    assert waiting["permission"]["decided_at"] is None
    assert [s["label"] for s in waiting["steps"] if s["kind"] == "permission"] == ["caregiver permission: requested, waiting"]
    approved = build_trace(scn, _at("2026-01-17T02:45:00-05:00"))
    assert approved["permission"]["status"] == "approved"
    assert approved["permission"]["actor"] == "family_caregiver"


def test_permission_never_changes_readiness_or_verification(scn):
    at = _at(AT_0231)
    plain = build_trace(scn, at)
    declined = build_trace(scn, at, caregiver_decision={"decision": "declined", "actor": "family_caregiver", "decided_at": AT_0231})
    assert declined["permission"]["status"] == "declined"
    assert declined["readiness"] == plain["readiness"]
    assert declined["verification"] == plain["verification"]
