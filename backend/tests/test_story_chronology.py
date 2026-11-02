"""The night happens in an order a person can follow. Expected times are written by hand."""
import json
import re
from datetime import datetime
from pathlib import Path

from aria_home.declined_view import declined_view
from aria_home.public_demo import CHECKPOINTS
from aria_home.scenario import load_scenario
from aria_home.transcribe import find_recorded_transcript, load_recorded_transcripts

BACKEND = Path(__file__).resolve().parent.parent
FIXTURE = BACKEND / "scenarios" / "care_home_v1"
TZ = "-05:00"


def at(day, hhmm):
    return datetime.fromisoformat(f"2026-01-{day}T{hhmm}:00{TZ}")


def scenario():
    return load_scenario(FIXTURE)


def event(scn, kind):
    return next(e for e in scn.events if e.kind == kind)


def room(scn):
    rows = [r for r in scn.records if r.source.value == "room_sensor" and r.quantity == "indoor_temp"]
    return sorted(rows, key=lambda r: r.observed_at)


def thermostat_times(scn):
    return sorted({r.observed_at for r in scn.records if r.source.value == "thermostat"})


def test_checkpoints_are_the_story_steps():
    assert [c[11:16] for c in CHECKPOINTS["care_home_v1"]] == ["19:20", "21:00", "21:41", "22:46", "23:31", "00:21", "00:31", "01:41", "01:51", "07:01"]


def test_events_run_in_the_order_they_could_happen():
    scn = scenario()
    assert event(scn, "caregiver_alert").available_at == at(16, "22:46")
    assert event(scn, "caregiver_hvac_authorized").available_at == at(16, "22:47")
    assert event(scn, "hvac_request").event_time == at(16, "22:50")
    assert event(scn, "technician_arrival").event_time == at(16, "23:30")
    assert event(scn, "service_visit").available_at == at(17, "00:15")
    assert event(scn, "hvac_completion_report").available_at == at(17, "01:50")
    order = ["caregiver_alert", "caregiver_hvac_authorized", "hvac_request", "technician_arrival", "service_visit", "hvac_completion_report"]
    times = [event(scn, kind).available_at for kind in order]
    assert times == sorted(times)


def test_technician_arrives_within_an_hour_of_the_ask():
    scn = scenario()
    waited = event(scn, "technician_arrival").event_time - event(scn, "caregiver_alert").available_at
    assert waited.total_seconds() == 44 * 60


def test_room_never_rises_before_the_repair_ends():
    rows = [r for r in room(scenario()) if at(16, "22:45") <= r.observed_at <= at(17, "00:15")]
    assert rows[0].value == 62.0
    assert rows[-1].value == 56.6
    assert all(later.value <= earlier.value for earlier, later in zip(rows, rows[1:]))


def test_room_rises_as_soon_as_the_repair_ends_and_reaches_target_fast():
    rows = {r.observed_at: r.value for r in room(scenario())}
    assert rows[at(17, "00:20")] > rows[at(17, "00:15")]
    assert rows[at(17, "01:10")] == 68.0
    held = [v for t, v in rows.items() if t >= at(17, "01:10")]
    assert min(held) >= 68.0
    assert (at(17, "01:40") - at(16, "22:46")).total_seconds() < 3 * 3600


def test_thermostat_is_silent_only_while_the_story_says_so():
    times = thermostat_times(scenario())
    assert not [t for t in times if at(16, "23:00") < t < at(17, "00:20")]
    assert at(16, "23:00") in times
    assert at(17, "00:20") in times
    assert all((b - a).total_seconds() <= 300 for a, b in zip(times, times[1:]) if not (a == at(16, "23:00") and b == at(17, "00:20")))


def test_blower_shows_no_heat_before_the_repair_ends():
    rows = [r for r in scenario().records if r.subject == "circuit-blower" and r.quantity == "circuit_power"]
    assert max(r.value for r in rows if r.observed_at <= at(17, "00:15")) < 50
    assert min(r.value for r in rows if r.observed_at >= at(17, "00:30")) > 400


def test_decline_has_no_technician_and_no_recovery():
    scn = declined_view(scenario())
    kinds = {e.kind for e in scn.events}
    assert not kinds & {"caregiver_hvac_authorized", "hvac_request", "technician_arrival", "service_visit", "hvac_completion_report"}
    rows = {r.observed_at: r.value for r in room(scn)}
    assert rows[at(17, "00:15")] == 56.6
    assert rows[at(17, "01:30")] == 52.0
    after = [v for t, v in sorted(rows.items()) if t >= at(16, "22:45")]
    assert all(later <= earlier for earlier, later in zip(after, after[1:]))
    assert 51.0 < rows[at(17, "07:00")] < 52.0
    assert not [t for t in thermostat_times(scn) if t > at(16, "23:00")]


def test_voice_note_names_the_restart_the_story_shows():
    match = find_recorded_transcript(load_recorded_transcripts(BACKEND / "eval"), "care_home_v1")
    assert "12 15" in match["entry"]["transcript"]


def test_no_old_timeline_left_in_the_story_data():
    old = re.compile(r"\b(01:30|02:31|02:45|03:30|04:15|04:20|04:21|04:51|05:50|06:21|06:45)\b|four fifteen|\b4 15\b")
    labels = json.dumps([e.payload for e in scenario().events if e.kind != "confirmation_request"])
    assert not old.search(labels)
    manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
    assert not old.search(manifest["description"])
    assert not old.search((BACKEND / "fixtures" / "voice" / "technician-note-script.txt").read_text(encoding="utf-8"))
