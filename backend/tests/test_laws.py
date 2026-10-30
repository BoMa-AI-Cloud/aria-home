"""Regression tests: one per ARIA law, each proving rejection and acceptance."""

from pathlib import Path

from aria_home import laws
from aria_home.laws import CHECKS, active_model_laws, check_output, load_laws

AT = "2026-01-17T07:00:00-05:00"


def _record(record_id, source="thermostat", quantity="indoor_temp", value=68.0, unit="F",
            observed=AT, received=AT, cadence=300, subject="demo-house/main"):
    return {
        "id": record_id, "source": source, "kind": "measurement", "subject": subject,
        "quantity": quantity, "value": value, "unit": unit,
        "observed_at": observed, "received_at": received, "expected_cadence_s": cadence,
    }


def _metric(record_id, data):
    return {"id": record_id, "type": "metric", "name": "circuit_activity", "data": data}


def _pack(*evidence):
    return {"at": AT, "evidence": list(evidence), "evidence_ids": [e["id"] for e in evidence]}


def test_registry_seed():
    registry = load_laws()
    assert registry["version"] == laws.LAWS_VERSION
    active = active_model_laws(registry)
    assert len(active) == 8
    for law in active:
        assert law["id"] and law["statement"] and law["origin"] == "design"
        assert law["status"] == "active" and law["check"] in CHECKS


def test_proposed_law_never_enforces():
    registry = load_laws()
    proposed = [law for law in registry["model_laws"] if law.get("status") == "proposed"]
    assert proposed
    output = {"hypotheses": [{"text": "The home is on track from the mild forecast", "supporting_ids": ["w1"], "conflicting_ids": []}]}
    pack = _pack({"id": "w1", "source": "weather", "kind": "forecast", "subject": "demo-house/main",
                  "quantity": "outdoor_temp_forecast", "value": 40.0, "unit": "F",
                  "observed_at": AT, "received_at": AT, "expected_cadence_s": 3600})
    assert check_output(output, pack) == []
    assert CHECKS["check_weather_never_decides"](output, pack, AT) is not None


def test_no_heat_from_watts():
    pack = _pack(_metric("metric:circuit_activity:furnace", {"max_w": 900.0, "unit": "W"}),
                  _record("r-temp"))
    bad = {"hypotheses": [{"text": "Warming is occurring; the heater is producing heat",
                            "supporting_ids": ["metric:circuit_activity:furnace"], "conflicting_ids": []}]}
    hits = check_output(bad, pack)
    assert [v["law"] for v in hits] == ["no-heat-from-watts"]
    good = {"hypotheses": [{"text": "Warming is occurring per the room reading",
                             "supporting_ids": ["metric:circuit_activity:furnace", "r-temp"], "conflicting_ids": []}]}
    assert check_output(good, pack) == []


def test_ack_is_not_resolution():
    bad = {"interpretation": "The notice was acknowledged by the manager, so the issue stands resolved."}
    assert [v["law"] for v in check_output(bad)] == ["ack-is-not-resolution"]
    good = {"interpretation": "The notice was acknowledged by the manager; acknowledged, not resolved."}
    assert check_output(good) == []


def test_reconnect_proves_nothing():
    bad = {"interpretation": "The thermostat reconnected and is back online, which proves the heating is working again."}
    assert [v["law"] for v in check_output(bad)] == ["reconnect-proves-nothing"]
    good = {"interpretation": "The thermostat reconnected; recovery is still unverified."}
    assert check_output(good) == []


def test_human_report_is_not_measurement():
    bad = {"facts": [{"claim_type": "current_temperature", "evidence_id": "human-report:technician-note-synthetic",
                      "field": "value", "value": 68.0, "unit": "F"}]}
    assert [v["law"] for v in check_output(bad)] == ["human-report-is-not-measurement"]
    good = {"facts": [{"claim_type": "current_temperature", "evidence_id": "r-temp",
                       "field": "value", "value": 68.0, "unit": "F"}]}
    assert check_output(good, _pack(_record("r-temp"))) == []


def test_no_detection_is_not_safe():
    bad = {"interpretation": "No frost was detected, so the home is all clear."}
    assert [v["law"] for v in check_output(bad)] == ["no-detection-is-not-safe"]
    good = {"interpretation": "No frost was detected; that is no detection, never an all-clear."}
    assert check_output(good) == []


def test_stale_is_not_current():
    stale = _record("r-old", observed="2026-01-17T05:00:00-05:00", received="2026-01-17T05:00:00-05:00")
    bad = {"observations": [{"kind": "temperature_drop", "claim": "Indoor temperature is currently 60 F",
                              "evidence_ids": ["r-old"], "values": {"value": 60.0, "unit": "F"}}]}
    hits = check_output(bad, _pack(stale, _record("r-old2", value=60.0, observed="2026-01-17T05:00:00-05:00", received="2026-01-17T05:00:00-05:00")))
    assert "stale-is-not-current" in [v["law"] for v in hits]
    fresh = _record("r-now", value=60.0)
    good = {"observations": [{"kind": "temperature_drop", "claim": "Indoor temperature is currently 60 F",
                               "evidence_ids": ["r-now"], "values": {"value": 60.0, "unit": "F"}}]}
    assert check_output(good, _pack(fresh)) == []


def test_conflicts_block_success():
    first = _record("r-a", source="room_sensor", value=60.0, observed="2026-01-17T06:00:00-05:00", received="2026-01-17T06:30:00-05:00")
    second = _record("r-b", source="room_sensor", value=70.0, observed="2026-01-17T06:00:00-05:00", received="2026-01-17T06:30:00-05:00")
    pack = _pack(first, second)
    bad = {"interpretation": "The goal is met and the home will be ready."}
    assert [v["law"] for v in check_output(bad, pack)] == ["conflicts-block-success"]
    good = {"interpretation": "The readings conflict, so the goal cannot be judged yet."}
    assert check_output(good, pack) == []


def test_no_images_or_personal_in_hvac():
    bad = {"audience": "hvac_company",
           "payload": {"audience": "hvac_company", "kind": "hvac_request", "property_label": "demo",
                       "access_note": "note", "image_url": "http://example.invalid/x.webp"}}
    assert [v["law"] for v in check_output(bad)] == ["no-images-or-personal-in-hvac"]
    good = {"audience": "hvac_company",
            "payload": {"audience": "hvac_company", "kind": "hvac_request", "property_label": "demo",
                        "access_note": "note", "relevant_observations": ["reading 60 F"]}}
    assert check_output(good) == []


def test_investigation_rejects_law_violation_by_name():
    import json
    from datetime import datetime

    from aria_home.investigator import investigate
    from aria_home.provider import MockProvider
    from aria_home.scenario import load_scenario

    scenario = load_scenario(Path(__file__).resolve().parent.parent / "scenarios" / "care_home_v1")
    at = datetime.fromisoformat("2026-01-17T02:31:00-05:00")
    first = investigate(scenario, at, provider=MockProvider())
    assert first.output is not None
    payload = first.output.model_dump(mode="json")
    assert payload["facts"], "mock investigation must cite at least one fact"
    payload["hypotheses"].append({"text": "The notice was acknowledged, so the issue stands resolved.",
                                  "supporting_ids": [payload["facts"][0]["evidence_id"]], "conflicting_ids": []})

    class _TextProvider:
        mode = "mock"
        model_id = "muse-spark-1.3"

        def generate(self, prompt, max_tokens=None):
            return {"ok": True, "text": json.dumps(payload), "mode": "mock",
                    "answered_model": "muse-spark-1.3", "requested_model": "muse-spark-1.3",
                    "latency_ms": 0.0, "input_tokens": None, "output_tokens": None,
                    "error": None, "stop_reason": None}

    result = investigate(scenario, at, provider=_TextProvider())
    assert result.status == "rejected"
    assert any(reason.startswith("law ack-is-not-resolution") for reason in result.reasons)


def test_mock_investigation_carries_no_law_reasons():
    from datetime import datetime

    from aria_home.investigator import investigate
    from aria_home.provider import MockProvider
    from aria_home.scenario import load_scenario

    scenario = load_scenario(Path(__file__).resolve().parent.parent / "scenarios" / "care_home_v1")
    result = investigate(scenario, datetime.fromisoformat("2026-01-17T02:31:00-05:00"), provider=MockProvider())
    assert not [reason for reason in result.reasons if reason.startswith("law ")]


def test_recorded_review_law_violation_rejects_review():
    from aria_home.review import recorded_review_for

    entries = [{"entry": {"scenario_id": "s", "evaluated_at_utc": AT, "input_revision": "r",
                          "review": {"verdict": "no_issues",
                                     "issues": [{"kind": "missing_context", "evidence_ids": ["e1"],
                                                 "note": "All clear: the home is confirmed safe"}]}}}]
    assert recorded_review_for(entries, "s", AT, "r", ["e1"])["review"] is None
    entries[0]["entry"]["review"]["issues"][0]["note"] = "Check the trend first"
    assert recorded_review_for(entries, "s", AT, "r", ["e1"])["review"] is not None


def test_no_route_can_call_live_watcher():
    source = (Path(__file__).resolve().parent.parent / "aria_home" / "app.py").read_text(encoding="utf-8")
    assert "request_live_watcher" not in source
    assert "activate_law" not in source


def test_public_mode_never_constructs_live_watcher():
    for name in ("recorded.py", "public_demo.py"):
        source = (Path(__file__).resolve().parent.parent / "aria_home" / name).read_text(encoding="utf-8")
        assert "request_live_watcher" not in source
