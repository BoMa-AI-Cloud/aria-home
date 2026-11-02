"""The care story's alert ladder and the warming low.

Expected values are written by hand from scenarios/care_home_v1/room_sensor.json:
the room reads 66.0 F at 21:41, 62.0 F at 22:46, falls to its 56.6 F low at 00:15
and reads 59.7 F at 00:30, against a 68 F target.
"""
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from aria_home.declined_view import declined_view
from aria_home.evaluation import FOLLOWUP_CREATED_AT
from aria_home.notifications import caregiver_alert_level
from aria_home.outcomes import follow_up_for
from aria_home.scenario import load_scenario
from aria_home.verification import build_evidence_timeline, verify_recovery

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"
CARE = "care_home_v1"
AT_2100 = "2026-01-16T21:00:00-05:00"
AT_2141 = "2026-01-16T21:41:00-05:00"
AT_2246 = "2026-01-16T22:46:00-05:00"
AT_0031 = "2026-01-17T00:31:00-05:00"
REQUEST_62 = "cooling (62 F, 6 F below the 68 F target, furnace reported idle since 4:00 PM)"


def _readiness(status, gap=None, hours=None):
    inputs = {}
    if gap is not None:
        inputs["gap_f"] = gap
    if hours is not None:
        inputs["hours_to_arrival"] = hours
    return {"status": status, "inputs": inputs}


@pytest.mark.parametrize(
    "readiness, expected",
    [
        (_readiness("on_track", gap=0.4, hours=9), "none"),
        (_readiness("at_risk", gap=-1.9, hours=9), "none"),
        (_readiness("at_risk", gap=-2.0, hours=9), "notice"),
        (_readiness("at_risk", gap=-5.9, hours=9), "notice"),
        (_readiness("at_risk", gap=-6.0, hours=9), "alert"),
        (_readiness("at_risk", gap=-3, hours=1.5), "alert"),
        (_readiness("at_risk", gap=-3, hours=3), "notice"),
        (_readiness("at_risk", hours=9), "alert"),
        (_readiness("cannot_tell"), "alert"),
        (_readiness("arrival_passed", gap=-16, hours=-1), "none"),
    ],
    ids=[
        "on_track",
        "gap-1.9",
        "gap-2.0",
        "gap-5.9",
        "gap-6.0",
        "backstop-1.5h",
        "gap-3-with-3h",
        "gap-missing",
        "cannot_tell",
        "arrival_passed",
    ],
)
def test_caregiver_alert_level_table(readiness, expected):
    assert caregiver_alert_level(readiness) == expected


def _client(tmp_path, monkeypatch):
    from aria_home.app import create_app
    for var in ("ARIA_HOME_MODEL_ENABLED", "ARIA_HOME_WHATSAPP_LIVE", "ARIA_HOME_EMPORIA_LIVE",
                "ARIA_HOME_VISUAL_LIVE", "ARIA_HOME_NEST_LIVE", "ARIA_HOME_E2E_HOOKS", "MODEL_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("ARIA_HOME_REVIEWS_DIR", str(tmp_path / "reviews"))
    monkeypatch.setenv("ARIA_HOME_CORRECTIONS_DIR", str(tmp_path / "corrections"))
    return create_app().test_client()


def _post(client, at):
    return client.post("/api/investigations", query_string={"scenario": CARE, "at": at}).get_json()


@pytest.mark.parametrize("at", [AT_2100, AT_2141])
def test_before_the_alert_gap_nobody_is_asked(tmp_path, monkeypatch, at):
    client = _client(tmp_path, monkeypatch)
    body = _post(client, at)
    assert body["follow_up"] is None
    assert body["notifications"] == []
    assert not [n for n in body["notifications"] if n["audience"] == "family_caregiver"]
    missing = client.get(f"/api/follow-ups/{body['investigation_id']}", query_string={"at": at}).get_json()
    assert missing.get("error") == "follow-up not found"


def test_2141_is_at_risk_and_the_activity_records_the_notice(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    body = _post(client, AT_2141)
    assert body["computed_readiness"] == "at_risk"
    text = body["activity"]["text"]
    assert "Noticed" in text
    assert "66" in text
    assert "6 F" in text
    assert body["activity"]["source"] == "computed:notice"


def test_2246_creates_the_request_with_the_62_f_text(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    body = _post(client, AT_2246)
    assert body["follow_up"] is not None
    alert = next(n for n in body["notifications"] if n["audience"] == "family_caregiver")
    assert alert["kind"] == "caregiver_alert"
    follow = client.get(f"/api/follow-ups/{body['investigation_id']}", query_string={"at": AT_2246}).get_json()
    permission = follow["caregiver_permission"]
    assert REQUEST_62 in permission["text"]
    assert permission["requested_at"] == AT_2246
    assert permission["status"] == "waiting"


def _care():
    return load_scenario(SCENARIOS_DIR / CARE)


def _follow_up_from_2246(scenario):
    return follow_up_for(scenario, "alert-ladder", datetime.fromisoformat(AT_2246))


def test_0031_is_warming_observed_from_the_low():
    scenario = _care()
    result = verify_recovery(scenario, _follow_up_from_2246(scenario), datetime.fromisoformat(AT_0031))
    assert result["stage"] == "warming_observed"


def test_timeline_first_warming_is_at_0025():
    scenario = _care()
    entries = build_evidence_timeline(scenario, _follow_up_from_2246(scenario), datetime.fromisoformat(AT_0031))
    warming = [e for e in entries if e["kind"] == "warming_observed"]
    assert warming, "no warming entry on the timeline by 00:31"
    observed = warming[0]["observed_at"]
    assert observed == datetime.fromisoformat("2026-01-17T00:25:00-05:00")


def test_a_room_that_keeps_falling_never_reaches_warming():
    scenario = declined_view(_care())
    follow_up = _follow_up_from_2246(scenario)
    at = datetime.fromisoformat(AT_2246) + timedelta(minutes=30)
    end = datetime.fromisoformat("2026-01-17T07:01:00-05:00")
    while at <= end:
        assert verify_recovery(scenario, follow_up, at)["stage"] != "warming_observed", at
        at += timedelta(minutes=30)
    entries = build_evidence_timeline(scenario, follow_up, end)
    assert not [e for e in entries if e["kind"] == "warming_observed"]


def test_evaluation_followup_opens_at_2246():
    assert FOLLOWUP_CREATED_AT[CARE] == AT_2246
