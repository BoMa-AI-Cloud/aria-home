"""Tests for the anomaly watcher: validation, verification, correction loop."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from aria_home.eligibility import is_fresh
from aria_home.investigator import build_evidence_pack
from aria_home.scenario import load_scenario
from aria_home.watcher import (
    NO_RECORDED_WATCHER_LABEL,
    NO_TEXT_REASON,
    WATCHER_PROMPT_VERSION,
    build_revision_prompt,
    build_watcher_prompt,
    code_detections,
    find_all_recorded_watchers,
    find_recorded_watcher,
    is_unreadable_rejection,
    load_correction_records,
    load_recorded_watchers,
    newest_recorded_watcher,
    parse_watcher_output,
    public_watcher,
    request_live_watcher,
    run_watcher,
    save_correction_record,
    verify_observation,
    verify_watcher_output,
    watcher_identity,
)

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"
AT = datetime.fromisoformat("2026-01-17T02:31:00-05:00")


def _care():
    return load_scenario(SCENARIOS_DIR / "care_home_v1")


def _fresh_indoor_obs(scenario, at):
    pack = build_evidence_pack(scenario, at)
    for item in pack["evidence"]:
        if not isinstance(item, dict) or "data" in item:
            continue
        if item.get("quantity") != "indoor_temp" or item.get("value") is None:
            continue
        if not is_fresh(item, at):
            continue
        return pack, {"kind": "temperature_drop", "claim": f"Room reading {item['value']} {item['unit']} noted",
                      "evidence_ids": [item["id"]],
                      "values": {"value": item["value"], "unit": item["unit"], "at": item["observed_at"]}}
    raise AssertionError("no fresh indoor reading in pack")


class _ScriptProvider:
    mode = "mock"
    model_id = "muse-spark-1.3"

    def __init__(self, texts):
        self.texts = list(texts)
        self.calls = 0

    def generate(self, prompt, max_tokens=None):
        self.calls += 1
        return {"ok": True, "text": self.texts[min(self.calls - 1, len(self.texts) - 1)],
                "mode": "mock", "answered_model": "muse-spark-1.3",
                "requested_model": "muse-spark-1.3", "latency_ms": 0.0,
                "input_tokens": None, "output_tokens": None, "error": None, "stop_reason": None}


def test_parse_validates_contract():
    parsed, reasons = parse_watcher_output({"observations": []})
    assert parsed == {"observations": []} and reasons == []
    _, reasons = parse_watcher_output({"observations": [{"kind": "guessing", "claim": "x", "evidence_ids": ["e"], "values": {}}]})
    assert any("unknown kind" in r for r in reasons)
    _, reasons = parse_watcher_output({"observations": [{"kind": "other", "claim": "x" * 201, "evidence_ids": ["e"], "values": {}}]})
    assert any("200" in r for r in reasons)
    _, reasons = parse_watcher_output({"observations": [{"kind": "other", "claim": "x", "evidence_ids": [], "values": {}}]})
    assert any("evidence_ids" in r for r in reasons)
    _, reasons = parse_watcher_output("not json")
    assert reasons


def test_verify_rejects_unknown_id_value_mismatch_and_stale():
    pack = {"at": "2026-01-17T07:00:00-05:00",
            "evidence": [{"id": "r1", "source": "thermostat", "kind": "measurement", "subject": "demo-house/main",
                          "quantity": "indoor_temp", "value": 60.0, "unit": "F",
                          "observed_at": "2026-01-17T07:00:00-05:00", "received_at": "2026-01-17T07:00:00-05:00",
                          "expected_cadence_s": 300}],
            "evidence_ids": ["r1"]}
    at = datetime.fromisoformat("2026-01-17T07:00:00-05:00")
    obs = {"kind": "temperature_drop", "claim": "c", "evidence_ids": ["nope"], "values": {}}
    assert any("unknown evidence id" in r for r in verify_observation(obs, pack, at))
    obs = {"kind": "temperature_drop", "claim": "c", "evidence_ids": ["r1"], "values": {"value": 70.0}}
    assert any("does not match" in r for r in verify_observation(obs, pack, at))
    stale_pack = {"at": "2026-01-17T07:00:00-05:00",
                  "evidence": [{"id": "r1", "source": "thermostat", "kind": "measurement", "subject": "demo-house/main",
                                "quantity": "indoor_temp", "value": 60.0, "unit": "F",
                                "observed_at": "2026-01-17T05:00:00-05:00", "received_at": "2026-01-17T05:00:00-05:00",
                                "expected_cadence_s": 300}],
                  "evidence_ids": ["r1"]}
    obs = {"kind": "temperature_drop", "claim": "c", "evidence_ids": ["r1"], "values": {"value": 60.0}}
    assert any("not fresh" in r for r in verify_observation(obs, stale_pack, at))


def test_correction_loop_passes_on_revision():
    scenario = _care()
    pack, good = _fresh_indoor_obs(scenario, AT)
    bad = json.dumps({"observations": [{"kind": "temperature_drop", "claim": "bad reading",
                                         "evidence_ids": ["no-such-id"], "values": {}}]})
    result = run_watcher(scenario, AT, _ScriptProvider([bad, json.dumps({"observations": [good]})]))
    assert result["final_result"] == "corrected and verified"
    assert result["observations"][0]["status"] == "corrected and verified"
    assert result["observations"][0]["notice"] == "noticed by the model, confirmed by the evidence check"
    record = result["correction_record"]
    assert record["original_claim"] is not None and record["failed_checks"] and record["revision_claim"] is not None
    assert record["final_result"] == "corrected and verified"


def test_correction_loop_rejects_after_two_failures():
    scenario = _care()
    bad = json.dumps({"observations": [{"kind": "temperature_drop", "claim": "bad reading",
                                         "evidence_ids": ["no-such-id"], "values": {}}]})
    provider = _ScriptProvider([bad, bad])
    result = run_watcher(scenario, AT, provider)
    assert provider.calls == 2
    assert result["final_result"] == "rejected"
    assert result["observations"] == [] and result["lowers_risk"] is False
    assert result["correction_record"]["final_result"] == "rejected"


def test_revision_introducing_new_violation_is_rejected():
    scenario = _care()
    pack, good = _fresh_indoor_obs(scenario, AT)
    first = json.dumps({"observations": [{"kind": "temperature_drop", "claim": "bad reading",
                                           "evidence_ids": ["no-such-id"], "values": {}}]})
    revised = dict(good, claim="All clear: the home is confirmed safe")
    result = run_watcher(scenario, AT, _ScriptProvider([first, json.dumps({"observations": [revised]})]))
    assert result["final_result"] == "rejected"
    assert any("law no-detection-is-not-safe" in check for check in result["failed_checks"])


def test_empty_watcher_never_lowers_risk_and_code_still_alerts():
    scenario = _care()
    result = run_watcher(scenario, AT, _ScriptProvider([json.dumps({"observations": []}), json.dumps({"observations": []})]))
    assert result["observations"] == [] and result["lowers_risk"] is False
    assert result["code_detections"]
    assert result["raise_caregiver_notice"] is True


def test_code_detections_quiet_pack_raises_nothing():
    scenario = _care()
    pack = build_evidence_pack(scenario, AT)
    pack["readiness"] = {"status": "on_track", "reasons": []}
    pack["source_statuses"] = [{"source": "thermostat", "availability": "available"}]
    pack["metrics"] = {"circuits": {}}
    assert code_detections(scenario, AT, pack) == []


def test_prompt_carries_laws_and_ledger_as_in_context_examples():
    from aria_home import laws as laws_module

    scenario = _care()
    pack = build_evidence_pack(scenario, AT)
    correction = {"original_claim": "old claim", "failed_checks": ["unknown evidence id: x"],
                  "revision_claim": "fixed claim", "final_result": "corrected and verified"}
    prompt = build_watcher_prompt(pack, laws_module.load_laws(), [correction])
    assert "no-heat-from-watts" in prompt and "old claim" in prompt and "not retrained" in prompt
    revision = build_revision_prompt("{}", ["unknown evidence id: x"], pack)
    assert "unknown evidence id: x" in revision


def test_recorded_replay_with_provenance_and_empty_fallback(tmp_path):
    scenario = _care()
    pack, good = _fresh_indoor_obs(scenario, AT)
    identity = watcher_identity(scenario, AT)
    assert identity["watcher_prompt_version"] == WATCHER_PROMPT_VERSION
    entry = {"scenario_id": identity["scenario_id"], "evaluated_at_utc": identity["evaluated_at_utc"],
             "input_revision": identity["input_revision"], "laws_version": identity["laws_version"],
             "watcher_prompt_version": WATCHER_PROMPT_VERSION, "model_id": "muse-spark-1.3",
             "provider_route": "mock", "recorded_at": "2026-10-29T00:00:00Z",
             "output": {"observations": [good]}}
    found = find_recorded_watcher([{"entry": entry, "source": "test"}], identity["scenario_id"],
                                  identity["evaluated_at_utc"], identity["input_revision"], identity["laws_version"])
    assert found is not None
    result = public_watcher(scenario, AT, entries=[{"entry": entry, "source": "test"}])
    assert result["model_observations"][0]["status"] == "confirmed"
    provenance = result["provenance"]
    assert (provenance["model_id"], provenance["provider_route"], provenance["recorded_at"],
            provenance["input_revision"], provenance["laws_version"]) == \
        ("muse-spark-1.3", "mock", "2026-10-29T00:00:00Z", identity["input_revision"], identity["laws_version"])
    empty = public_watcher(scenario, AT, entries=[])
    assert empty["model_observations"] == [] and empty["model_note"] == NO_RECORDED_WATCHER_LABEL
    assert empty["provenance"] is None and empty["code_detections"]


def test_correction_records_roundtrip(tmp_path):
    record = {"scenario_id": "s", "final_result": "corrected and verified"}
    path = save_correction_record(record, directory=tmp_path)
    assert path.name.startswith("corrections-")
    assert load_correction_records(directory=tmp_path) == [record]


def test_live_watcher_refused_without_explicit_enablement():
    assert request_live_watcher("{}", env={}) == {"ok": False, "error": "disabled", "text": None}


def test_verify_applies_active_laws():
    pack = {"at": "2026-01-17T07:00:00-05:00", "evidence": [], "evidence_ids": []}
    at = datetime.fromisoformat("2026-01-17T07:00:00-05:00")
    parsed = {"observations": []}
    assert verify_watcher_output(parsed, pack, at) == []


def _watcher_entry(identity, *, status, recorded_at, failed_checks=()):
    return {"scenario_id": identity["scenario_id"], "evaluated_at_utc": identity["evaluated_at_utc"],
            "input_revision": identity["input_revision"], "laws_version": identity["laws_version"],
            "watcher_prompt_version": WATCHER_PROMPT_VERSION, "model_id": "muse-spark-1.3",
            "provider_route": "mock", "recorded_at": recorded_at,
            "status": status, "final_result": status, "failed_checks": list(failed_checks),
            "output": {"observations": []}}


def _find_args(identity):
    return (identity["scenario_id"], identity["evaluated_at_utc"], identity["input_revision"], identity["laws_version"])


def test_find_serves_newest_verified_when_identity_repeats():
    identity = watcher_identity(_care(), AT)
    entries = [
        {"entry": _watcher_entry(identity, status="confirmed", recorded_at="2026-10-30T19:00:00+00:00"), "source": "a"},
        {"entry": _watcher_entry(identity, status="corrected and verified", recorded_at="2026-10-30T19:01:00+00:00"), "source": "b"},
        {"entry": _watcher_entry(identity, status="confirmed", recorded_at="2026-10-30T19:02:00+00:00"), "source": "c"},
    ]
    assert find_recorded_watcher(entries, *_find_args(identity))["source"] == "c"
    assert newest_recorded_watcher(find_all_recorded_watchers(entries, *_find_args(identity)))["source"] == "c"


def test_find_prefers_verified_over_newer_real_rejection():
    identity = watcher_identity(_care(), AT)
    entries = [
        {"entry": _watcher_entry(identity, status="confirmed", recorded_at="2026-10-30T19:00:00+00:00"), "source": "verified"},
        {"entry": _watcher_entry(identity, status="rejected", recorded_at="2026-10-30T19:05:00+00:00",
                                 failed_checks=["observation value does not match evidence room-care-1630"]), "source": "rejected"},
    ]
    assert find_recorded_watcher(entries, *_find_args(identity))["source"] == "verified"


def test_unreadable_rejection_never_hides_readable_entry():
    identity = watcher_identity(_care(), AT)
    for failed in (["invalid JSON: Expecting value: line 1 column 1 (char 0)"], [NO_TEXT_REASON]):
        assert is_unreadable_rejection({"final_result": "rejected", "failed_checks": failed}) is True
        entries = [
            {"entry": _watcher_entry(identity, status="rejected", recorded_at="2026-10-30T19:05:00+00:00",
                                     failed_checks=failed), "source": "unreadable"},
            {"entry": _watcher_entry(identity, status="confirmed", recorded_at="2026-10-30T19:00:00+00:00"), "source": "readable"},
        ]
        assert find_recorded_watcher(entries, *_find_args(identity))["source"] == "readable"
        assert find_recorded_watcher(list(reversed(entries)), *_find_args(identity))["source"] == "readable"


def test_real_code_check_rejection_is_not_unreadable_and_still_served():
    identity = watcher_identity(_care(), AT)
    failed = ["observation value does not match evidence room-care-1630: 71.0 != 52.0 (tolerance 0.15)"]
    assert is_unreadable_rejection({"final_result": "rejected", "failed_checks": failed}) is False
    assert is_unreadable_rejection({"final_result": "rejected", "failed_checks": failed + ["invalid JSON: x"]}) is False
    assert is_unreadable_rejection({"final_result": "confirmed", "failed_checks": []}) is False
    entries = [{"entry": _watcher_entry(identity, status="rejected", recorded_at="2026-10-30T19:05:00+00:00",
                                        failed_checks=failed), "source": "only"}]
    assert find_recorded_watcher(entries, *_find_args(identity))["source"] == "only"


def test_load_recorded_watchers_aggregates_repeat_identities(tmp_path):
    identity = watcher_identity(_care(), AT)
    unreadable = _watcher_entry(identity, status="rejected", recorded_at="2026-10-30T19:05:00+00:00",
                                failed_checks=["invalid JSON: Expecting value: line 1 column 1 (char 0)"])
    readable = _watcher_entry(identity, status="confirmed", recorded_at="2026-10-30T19:06:00+00:00")
    (tmp_path / "watchers-a.json").write_text(json.dumps({"watchers": [unreadable]}), encoding="utf-8")
    (tmp_path / "watchers-b.json").write_text(json.dumps({"watchers": [readable]}), encoding="utf-8")
    entries = load_recorded_watchers(tmp_path)
    assert len(entries) == 2
    assert find_recorded_watcher(entries, *_find_args(identity))["entry"] == readable
