import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aria_home.app as app_module
from aria_home.app import create_app
from aria_home.contracts import EvidenceRecord
from aria_home.eligibility import is_current_record, latest_current
from aria_home.investigator import build_evidence_pack, validate
from aria_home.outcomes import FollowUp, follow_up_for
from aria_home.readiness import compute_readiness
from aria_home.scenario import load_scenario
from aria_home.verification import build_evidence_timeline, verify_recovery

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "demo_video_v1"
TZ = timezone(timedelta(hours=-5))
ZONE = "demo-house/main"
REPORT_ID = "evt-video-hvac-completion-report"


def at(hour, minute=0, second=0):
    return datetime(2026, 1, 16, hour, minute, second, tzinfo=TZ)


def _copy(tmp_path, name):
    target = tmp_path / name
    target.mkdir()
    for path in SCENARIO_DIR.glob("*.json"):
        (target / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def _edit(target, filename, fn):
    path = target / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    data["records"] = fn(data["records"])
    path.write_text(json.dumps(data), encoding="utf-8")


def _verify(target, now):
    scenario = load_scenario(target)
    followup = follow_up_for(scenario, "inv-audit4", at(16, 31))
    return verify_recovery(scenario, followup, now), scenario


def _latest_room_copy(records, value=40.0, new_id=None):
    latest = next(r for r in records if r["observed_at"] == "2026-01-16T21:00:00-05:00")
    row = {**latest, "value": value}
    if new_id is not None:
        row["id"] = new_id
    return row


def _readiness(scenario, now):
    pack = build_evidence_pack(scenario, now)
    return compute_readiness(pack, now), pack


def test_same_id_contradiction_both_insertion_orders(tmp_path):
    for placement in ("append", "prepend"):
        target = _copy(tmp_path, f"sameid-{placement}")

        def add(records, placement=placement):
            copy = _latest_room_copy(records)
            return records + [copy] if placement == "append" else [copy] + records

        _edit(target, "room_sensor.json", add)
        result, scenario = _verify(target, at(21, 1))
        assert result["stage"] == "unable_to_verify", (placement, result["stage"])
        assert result["stage"] != "arrival_met"
        readiness, _ = _readiness(scenario, at(21, 1))
        assert readiness["status"] == "cannot_tell"
        assert any("conflict" in reason for reason in readiness["reasons"])


def test_different_id_conflict_both_id_orders_and_insertions(tmp_path):
    import itertools

    for prefix, placement in itertools.product(("aa-", "zz-"), ("append", "prepend")):
        target = _copy(tmp_path, f"diffid-{prefix.strip('-')}-{placement}")

        def add(records, prefix=prefix, placement=placement):
            copy = _latest_room_copy(records, new_id=f"{prefix}conflict")
            return records + [copy] if placement == "append" else [copy] + records

        _edit(target, "room_sensor.json", add)
        result, scenario = _verify(target, at(21, 1))
        assert result["stage"] == "unable_to_verify", (prefix, placement, result["stage"])
        readiness, _ = _readiness(scenario, at(21, 1))
        assert readiness["status"] == "cannot_tell"


def test_same_id_conflict_inside_hold_interval(tmp_path):
    target = _copy(tmp_path, "sameid-hold")

    def add(records):
        row = next(r for r in records if r["observed_at"] == "2026-01-16T20:05:00-05:00")
        return records + [{**row, "value": 40.0}]

    _edit(target, "room_sensor.json", add)
    result, _ = _verify(target, at(20, 21))
    assert result["stage"] == "unable_to_verify"
    assert result["stage"] != "goal_verified"


def test_identical_same_id_duplicate_collapses_to_one(tmp_path):
    target = _copy(tmp_path, "sameid-identical")

    def add(records):
        latest = next(r for r in records if r["observed_at"] == "2026-01-16T21:00:00-05:00")
        return records + [dict(latest)]

    _edit(target, "room_sensor.json", add)
    result, _ = _verify(target, at(21, 1))
    assert result["stage"] == "arrival_met"
    assert result["supporting_ids"].count("room-temp-2100") == 1
    assert len(result["supporting_ids"]) == len(set(result["supporting_ids"]))


def test_conflicts_outside_zone_and_window_do_not_block(tmp_path):
    target = _copy(tmp_path, "outside-scope")

    def add(records):
        latest = next(r for r in records if r["observed_at"] == "2026-01-16T21:00:00-05:00")
        early = next(r for r in records if r["observed_at"] == "2026-01-16T16:30:00-05:00")
        return records + [
            {**latest, "id": "other-zone-conflict", "subject": "demo-house/other", "value": 40.0},
            {**early, "id": "early-conflict", "value": 40.0},
        ]

    _edit(target, "room_sensor.json", add)
    result, scenario = _verify(target, at(21, 1))
    assert result["stage"] == "arrival_met"
    readiness, _ = _readiness(scenario, at(21, 1))
    assert readiness["status"] != "cannot_tell"


def test_api_regression_same_id_conflict_never_arrival_met(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    variant = _copy(tmp_path, "demo_v1")
    _edit(variant, "room_sensor.json", lambda records: records + [_latest_room_copy(records)])
    monkeypatch.setattr(app_module, "SCENARIO_PATH", tmp_path / "demo_v1")
    client = create_app().test_client()
    resp = client.post("/api/investigations?scenario=demo_video_v1&at=2026-01-16T16:31:00-05:00")
    assert resp.status_code == 200
    inv_id = resp.get_json()["investigation_id"]
    body = client.get(f"/api/follow-ups/{inv_id}?at=2026-01-16T21:01:00-05:00").get_json()
    assert body["verification"]["stage"] == "unable_to_verify"
    assert body["verification"]["stage"] != "arrival_met"
    kinds = [e["kind"] for e in body["evidence_timeline"]]
    assert "arrival_checked" not in kinds


def _item(rid, value, observed, received=None, source="room_sensor", subject=ZONE, cadence=300):
    received = received or observed + timedelta(seconds=20)
    return {
        "id": rid, "source": source, "kind": "measurement", "subject": subject, "quantity": "indoor_temp",
        "value": value, "unit": "F", "observed_at": observed.isoformat(), "received_at": received.isoformat(),
        "expected_cadence_s": cadence, "provenance": {"fixture_id": "test", "version": "1"},
    }


def _pack(now, items, last_value, last_observed, target=68.0):
    trend = {"sample_count": 5, "coverage": 1.0, "last_value": last_value, "unit": "F",
             "first_observed_at": (last_observed - timedelta(hours=2)).isoformat(),
             "last_observed_at": last_observed.isoformat(), "rate_per_hour": 0.0, "change": 0.0,
             "expected_cadence_s": 300}
    gap = {"gap": last_value - target, "unit": "F", "latest_value": last_value,
           "latest_observed_at": last_observed.isoformat(), "target_temp": target, "target_unit": "F"}
    evidence = list(items) + [
        {"id": "metric:indoor_trend", "type": "metric", "name": "indoor_trend", "data": trend},
        {"id": "metric:target_gap", "type": "metric", "name": "target_gap", "data": gap},
    ]
    pack = {
        "at": now.isoformat(),
        "trip": {"id": "t1", "property_id": "demo-house", "planned_arrival": (now + timedelta(hours=2)).isoformat()},
        "confirmation": {"trip_id": "t1", "property_id": "demo-house", "target_temp": target, "target_unit": "F"},
        "source_statuses": [],
        "metrics": {"zone": ZONE, "indoor_trend": trend, "target_gap": gap},
        "evidence": evidence,
        "evidence_ids": [item["id"] for item in evidence],
    }
    readiness = compute_readiness(pack, now)
    pack["readiness"] = dict(readiness)
    pack["canonical_readiness"] = dict(readiness)
    pack["computed_readiness"] = readiness["status"]
    pack["readiness_policy_version"] = readiness["policy_version"]
    return pack


def _output_for(fact, pack, now):
    return {
        "facts": [fact],
        "interpretation": f"Indoor temperature is {fact['value']} F.",
        "hypotheses": [{"text": "The property may not be ready.", "supporting_ids": [fact["evidence_id"]], "conflicting_ids": []}],
        "unknowns": ["Equipment function is not established."],
        "clarification": "Who should respond?",
        "follow_up": {"observation": "Take another reading.", "when": (now + timedelta(minutes=30)).isoformat()},
        "readiness": pack["computed_readiness"],
        "limitations": ["Limited evidence."],
    }


def _fact(rid, value, observed):
    return {"claim_type": "current_temperature", "evidence_id": rid, "field": "value", "value": value, "unit": "F", "at": observed.isoformat()}


def test_current_claim_falls_back_across_newer_conflict_rejected():
    now = at(20, 21)
    items = [
        _item("room-old", 68.0, at(20, 15)),
        _item("room-cf-a", 69.0, at(20, 20)),
        _item("room-cf-b", 40.0, at(20, 20)),
    ]
    pack = _pack(now, items, 68.0, at(20, 15))
    assert pack["computed_readiness"] == "cannot_tell"
    reasons = validate(_output_for(_fact("room-old", 68.0, at(20, 15)), pack, now), pack)
    assert any("newer relevant" in r or "superseded" in r or "historical" in r for r in reasons)
    metric_fact = {"claim_type": "current_temperature", "evidence_id": "metric:indoor_trend", "field": "last_value", "value": 68.0, "unit": "F", "at": at(20, 15).isoformat()}
    metric_reasons = validate(_output_for(metric_fact, pack, now), pack)
    assert any("newer relevant" in r or "superseded" in r or "historical" in r for r in metric_reasons)
    assert latest_current(items, "indoor_temp", now, zone=ZONE) is None
    ok, _ = is_current_record(next(i for i in items if i["id"] == "room-old"), items, "indoor_temp", now, zone=ZONE)
    assert not ok


def test_current_claim_after_resolving_reading_passes():
    now = at(20, 26)
    items = [
        _item("room-old", 68.0, at(20, 15)),
        _item("room-cf-a", 69.0, at(20, 20)),
        _item("room-cf-b", 40.0, at(20, 20)),
        _item("room-new", 68.5, at(20, 25)),
    ]
    pack = _pack(now, items, 68.5, at(20, 25))
    assert validate(_output_for(_fact("room-new", 68.5, at(20, 25)), pack, now), pack) == []
    ok, _ = is_current_record(next(i for i in items if i["id"] == "room-new"), items, "indoor_temp", now, zone=ZONE)
    assert ok


def test_current_claim_stale_rejected():
    now = at(21, 30)
    items = [_item("room-old", 68.0, at(20, 15))]
    pack = _pack(now, items, 68.0, at(20, 15))
    reasons = validate(_output_for(_fact("room-old", 68.0, at(20, 15)), pack, now), pack)
    assert any("stale" in r or "historical" in r or "current" in r for r in reasons)


def test_current_claim_passes_when_newer_conflict_not_yet_received():
    now = at(20, 21)
    items = [
        _item("room-old", 68.0, at(20, 15)),
        _item("room-cf-a", 69.0, at(20, 20), received=at(20, 25)),
        _item("room-cf-b", 40.0, at(20, 20), received=at(20, 25)),
    ]
    pack = _pack(now, items, 68.0, at(20, 15))
    assert validate(_output_for(_fact("room-old", 68.0, at(20, 15)), pack, now), pack) == []


def test_current_claim_unaffected_by_other_zone_conflict():
    now = at(20, 21)
    items = [
        _item("room-old", 68.0, at(20, 15)),
        _item("other-a", 69.0, at(20, 20), subject="demo-house/other"),
        _item("other-b", 40.0, at(20, 20), subject="demo-house/other"),
    ]
    pack = _pack(now, items, 68.0, at(20, 15))
    assert validate(_output_for(_fact("room-old", 68.0, at(20, 15)), pack, now), pack) == []


def _record(rid, minute_offset, value=68.0, received_offset=None, source="room_sensor", unit="F"):
    observed = at(19, 0) + timedelta(minutes=minute_offset)
    if received_offset is None:
        received = observed + timedelta(seconds=20)
    else:
        received = at(19, 0) + timedelta(minutes=received_offset)
    return EvidenceRecord.model_validate({
        "id": rid, "source": source, "kind": "measurement", "subject": ZONE, "quantity": "indoor_temp",
        "value": value, "unit": unit, "observed_at": observed, "received_at": received,
        "expected_cadence_s": 300, "mode": "synthetic", "provenance": {"fixture_id": "audit4", "version": "1"},
    })


def _tstat(rid, minute_offset, base_hour=18):
    observed = datetime(2026, 1, 16, base_hour, 0, tzinfo=TZ) + timedelta(minutes=minute_offset)
    return EvidenceRecord.model_validate({
        "id": rid, "source": "thermostat", "kind": "measurement", "subject": ZONE, "quantity": "indoor_temp",
        "value": 68.2, "unit": "F", "observed_at": observed, "received_at": observed + timedelta(seconds=20),
        "expected_cadence_s": 300, "mode": "synthetic", "provenance": {"fixture_id": "audit4", "version": "1"},
    })


def _late_receipt_scenario(late_offsets):
    rooms = [
        _record(f"room-{m:02d}", m, received_offset=late_offsets.get(m))
        for m in (0, 5, 10, 15, 20, 25, 30)
    ]
    rooms += [_record(f"room-m{m:02d}", m) for m in (35, 40, 45, 50, 55, 60)]
    stats = [_tstat(f"tstat-{m:02d}", m) for m in range(0, 130, 5)]
    followup = FollowUp(
        investigation_id="audit4", created_at=at(18, 0), target_temp=68.0, target_unit="F",
        deadline=at(23, 0), zone=ZONE, cadence_s=300,
    )
    scenario = {"records": rooms + stats, "events": [], "trip": {"planned_arrival": at(21, 0)}}
    receipts = {r.id: r.received_at for r in rooms + stats}
    return scenario, followup, receipts


def _assert_knowledge_time(entries, receipts, now):
    for entry in entries:
        assert entry["first_known_at"] <= now, entry["kind"]
        deps = [receipts[i] for i in entry["supporting_ids"] if i in receipts]
        if deps:
            assert entry["first_known_at"] >= max(deps), entry["kind"]
        assert entry["observed_at"] <= entry["first_known_at"], entry["kind"]


def test_timeline_late_first_sample_knowledge_time():
    scenario, followup, receipts = _late_receipt_scenario({0: 60})
    early = build_evidence_timeline(scenario, followup, at(19, 31))
    assert "goal_verified" not in [e["kind"] for e in early]
    assert verify_recovery(scenario, followup, at(19, 31))["stage"] != "goal_verified"
    late = build_evidence_timeline(scenario, followup, at(20, 0))
    goal = next(e for e in late if e["kind"] == "goal_verified")
    assert goal["observed_at"] == at(19, 30)
    assert goal["first_known_at"] == at(20, 0)
    _assert_knowledge_time(late, receipts, at(20, 0))
    result = verify_recovery(scenario, followup, at(20, 0))
    assert result["stage"] == "goal_verified"
    assert result["goal_verified_at"] == goal["observed_at"]


def test_timeline_late_middle_and_endpoint_samples():
    scenario, followup, receipts = _late_receipt_scenario({15: 60})
    mid_early = build_evidence_timeline(scenario, followup, at(19, 31))
    goal = next(e for e in mid_early if e["kind"] == "goal_verified")
    assert goal["first_known_at"] == at(19, 30, 20)
    mid_late = build_evidence_timeline(scenario, followup, at(20, 0))
    assert next(e for e in mid_late if e["kind"] == "goal_verified")["first_known_at"] == at(20, 0)
    _assert_knowledge_time(mid_late, receipts, at(20, 0))

    scenario, followup, receipts = _late_receipt_scenario({30: 60})
    assert "goal_verified" not in [e["kind"] for e in build_evidence_timeline(scenario, followup, at(19, 31))]
    end_late = build_evidence_timeline(scenario, followup, at(20, 0))
    goal = next(e for e in end_late if e["kind"] == "goal_verified")
    assert goal["observed_at"] == at(19, 30)
    assert goal["first_known_at"] == at(20, 0)
    _assert_knowledge_time(end_late, receipts, at(20, 0))


def test_timeline_out_of_order_receipts_and_rewind():
    scenario, followup, receipts = _late_receipt_scenario({10: 40})
    entries = build_evidence_timeline(scenario, followup, at(19, 35))
    goal = next(e for e in entries if e["kind"] == "goal_verified")
    assert goal["observed_at"] == at(19, 30)
    assert goal["first_known_at"] <= at(19, 35)
    _assert_knowledge_time(entries, receipts, at(19, 35))
    later = build_evidence_timeline(scenario, followup, at(19, 45))
    assert next(e for e in later if e["kind"] == "goal_verified")["first_known_at"] == at(19, 40)
    rewound = build_evidence_timeline(scenario, followup, at(19, 31))
    assert verify_recovery(scenario, followup, at(19, 31))["stage"] == "goal_verified"
    assert next(e for e in rewound if e["kind"] == "goal_verified")["first_known_at"] == at(19, 30, 20)


def test_timeline_arrival_evidence_learned_after_arrival(tmp_path):
    target = _copy(tmp_path, "arrival-late")

    def delay(records):
        out = []
        for row in records:
            if row["observed_at"] in (
                "2026-01-16T20:20:00-05:00",
                "2026-01-16T20:25:00-05:00",
                "2026-01-16T20:30:00-05:00",
            ):
                row = {**row, "received_at": "2026-01-16T21:05:00-05:00"}
            out.append(row)
        return out

    _edit(target, "room_sensor.json", delay)
    scenario = load_scenario(target)
    followup = follow_up_for(scenario, "inv-arrival-late", at(16, 31))
    before = verify_recovery(scenario, followup, at(21, 1))
    assert before["stage"] != "arrival_met"
    after = verify_recovery(scenario, followup, at(21, 6))
    assert after["stage"] == "arrival_met"
    entries = build_evidence_timeline(scenario, followup, at(21, 6))
    arrival = next(e for e in entries if e["kind"] == "arrival_checked")
    assert arrival["observed_at"] == at(21, 0)
    assert arrival["first_known_at"] == at(21, 5)
    goal = next(e for e in entries if e["kind"] == "goal_verified")
    assert goal["first_known_at"] == at(21, 5)
    receipts = {r.id: r.received_at for r in scenario.records}
    _assert_knowledge_time(entries, receipts, at(21, 6))


def test_wrong_zone_thermostat_does_not_satisfy_recovery_gate(tmp_path):
    target = _copy(tmp_path, "wrong-zone-tstat")

    def strip_main(records):
        return [r for r in records if not (r["quantity"] == "indoor_temp" and r["subject"] == ZONE)]

    _edit(target, "thermostat.json", strip_main)

    _edit(
        target,
        "thermostat.json",
        lambda records: records
        + [
            {
                "id": f"tstat-other-temp-{stamp[11:13]}{stamp[14:16]}",
                "source": "thermostat",
                "kind": "measurement",
                "subject": "demo-house/other",
                "quantity": "indoor_temp",
                "value": 70.0,
                "unit": "F",
                "observed_at": stamp,
                "received_at": stamp[:17] + "20" + stamp[19:],
                "expected_cadence_s": 300,
                "mode": "synthetic",
                "provenance": {"fixture_id": "audit4", "version": "1"},
            }
            for stamp in (
                "2026-01-16T20:50:00-05:00",
                "2026-01-16T20:55:00-05:00",
                "2026-01-16T21:00:00-05:00",
            )
        ],
    )
    result, scenario = _verify(target, at(21, 1))
    assert result["stage"] == "telemetry_missing"
    assert result["stage"] != "arrival_met"
    assert not any("other" in sid for sid in result["supporting_ids"])
    entries = build_evidence_timeline(scenario, follow_up_for(scenario, "inv-wz", at(16, 31)), at(21, 1))
    assert "reporting_restored" not in [e["kind"] for e in entries]


def test_wrong_property_circuit_binding_is_not_equipment_support(tmp_path):
    target = _copy(tmp_path, "wrong-property-circuit")

    def rebind(records):
        out = []
        for row in records:
            if row["subject"] == "circuit-blower":
                row = {**row, "value": 900, "meter_id": "other-house-meter-9"}
            out.append(row)
        return out

    _edit(target, "electrical.json", rebind)
    result, _ = _verify(target, at(21, 1))
    assert result["stage"] == "arrival_met"
    assert not any("elec-video-blower" in sid for sid in result["supporting_ids"])


def test_temperature_success_carries_no_causal_repair_claim(tmp_path):
    target = _copy(tmp_path, "no-causal")
    result, _ = _verify(target, at(21, 1))
    assert result["stage"] == "arrival_met"
    assert not any("caus" in reason.lower() or "repair" in reason.lower() for reason in result["reasons"])
    assert any("separate equipment observation" in reason for reason in result["reasons"])
