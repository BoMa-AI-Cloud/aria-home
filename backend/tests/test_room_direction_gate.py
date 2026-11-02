"""The models are told which way the room is moving and what already happened, and code holds them to it."""
import json
from datetime import datetime
from pathlib import Path

from aria_home.investigator import SYSTEM_PROMPT, build_evidence_pack, validate
from aria_home.provider import MockProvider
from aria_home.scenario import load_scenario
from aria_home.watcher import verify_observation

FIXTURE = Path(__file__).resolve().parent.parent / "scenarios" / "care_home_v1"
TZ = "-05:00"


def _mock_text(scn, when):
    pack = build_evidence_pack(scn, when)
    return MockProvider().generate(SYSTEM_PROMPT + "\nEvidence pack (JSON):\n" + json.dumps(pack)).text


def at(day, hhmm):
    return datetime.fromisoformat(f"2026-01-{day}T{hhmm}:00{TZ}")


def pack_at(day, hhmm):
    scn = load_scenario(FIXTURE)
    when = at(day, hhmm)
    return scn, when, build_evidence_pack(scn, when)


def test_direction_at_each_part_of_the_night():
    expected = [("16", "22:46", "falling"), ("16", "23:31", "falling"), ("17", "00:31", "rising"), ("17", "01:51", "holding")]
    for day, hhmm, word in expected:
        assert pack_at(day, hhmm)[2]["room_direction"]["direction"] == word, hhmm


def test_actions_so_far_grow_with_the_night():
    kinds = lambda pack: [a["kind"] for a in pack["actions_so_far"]]
    assert kinds(pack_at("16", "21:41")[2]) == []
    assert kinds(pack_at("16", "22:46")[2]) == ["caregiver_alert"]
    assert "technician_arrival" in kinds(pack_at("16", "23:31")[2])
    assert "service_visit" not in kinds(pack_at("16", "23:31")[2])
    assert "service_visit" in kinds(pack_at("17", "00:21")[2])
    assert "hvac_completion_report" in kinds(pack_at("17", "01:51")[2])


def test_gate_rejects_falling_prose_while_the_room_rises():
    scn, when, pack = pack_at("17", "00:31")
    data = json.loads(_mock_text(scn, when))
    data["interpretation"] = "Readings keep falling, so the house may not be warm."
    assert any("must not describe it as falling" in r for r in validate(data, pack))


def test_gate_allows_falling_prose_while_the_room_falls():
    scn, when, pack = pack_at("16", "22:46")
    data = json.loads(_mock_text(scn, when))
    data["interpretation"] = "Readings keep falling, so the house may not be warm."
    assert not any("must not describe it as falling" in r for r in validate(data, pack))


def test_watcher_drop_is_rejected_while_the_room_rises():
    _, when, pack = pack_at("17", "00:31")
    obs = {"kind": "temperature_drop", "claim": "Room falling", "evidence_ids": ["metric:indoor_trend"], "values": {}}
    assert any("contradicts" in r for r in verify_observation(obs, pack, when))


def test_watcher_drop_is_allowed_while_the_room_falls():
    _, when, pack = pack_at("16", "22:46")
    obs = {"kind": "temperature_drop", "claim": "Room falling", "evidence_ids": ["metric:indoor_trend"], "values": {}}
    assert not any("contradicts" in r for r in verify_observation(obs, pack, when))


def test_watcher_cannot_cite_a_silent_thermostat_as_current():
    _, when, pack = pack_at("16", "23:31")
    source = next(e["id"] for e in pack["evidence"] if str(e["id"]) == "source:thermostat")
    obs = {"kind": "other", "claim": "Thermostat reads idle", "evidence_ids": [source], "values": {}}
    assert any("not current" in r for r in verify_observation(obs, pack, when))
    gap = {"kind": "telemetry_gap", "claim": "Thermostat is silent", "evidence_ids": [source], "values": {}}
    assert not any("not current" in r for r in verify_observation(gap, pack, when))
