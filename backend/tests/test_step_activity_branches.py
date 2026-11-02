"""Activity-line truth across all ten care_home_v1 steps and all branches.

Every activity line served by the API must be true as of the replay time:
after a decline, contact/visit/report events never appear as happened; a
decision recorded later never rewrites an earlier line; every line names a
source. Straight POST jumps (the explore path) must also agree.
"""
from datetime import datetime
from pathlib import Path

from aria_home.scenario import load_scenario
from aria_home.trace import step_activity

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"
CARE = "care_home_v1"

CARE_TIMES = [
    "2026-01-16T19:20:00-05:00",
    "2026-01-16T21:00:00-05:00",
    "2026-01-16T23:30:00-05:00",
    "2026-01-17T02:31:00-05:00",
    "2026-01-17T02:45:00-05:00",
    "2026-01-17T04:21:00-05:00",
    "2026-01-17T04:51:00-05:00",
    "2026-01-17T06:21:00-05:00",
    "2026-01-17T06:45:00-05:00",
    "2026-01-17T07:01:00-05:00",
]

FORBIDDEN = [
    "simulated ",
    "Simulated ",
    "Arrival",
    "arrival",
    "manager",
    "Manager",
    "trip",
    "Trip",
    "homeowner",
    "Homeowner",
    "monitor",
]

PERMISSION_LINE = "permission request sent to the family caregiver"
AUTH_LINE = "Family caregiver authorized contacting the HVAC company on file"
REPORT_LINE = "HVAC completion report (available to ARIA only after verification at 06:21; corroboration only)"
VISIT_LINE = "Technician visit 03:30-04:15 (does not by itself close anything)"


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


def _setup_branch(tmp_path, monkeypatch, decision=None, decided_at=CARE_TIMES[3]):
    client = _client(tmp_path, monkeypatch)
    body = _post(client, CARE_TIMES[2])
    investigation_id = body["investigation_id"]
    if decision is not None:
        alert = next(r for r in body["notifications"] if r["audience"] == "family_caregiver")
        resp = client.post(
            f"/api/notifications/{alert['id']}/caregiver-decision",
            json={"decision": decision, "at": decided_at, "scenario": CARE},
        )
        assert resp.status_code in (200, 201)
    return client, investigation_id


def _activities(client, investigation_id):
    lines = {}
    for index, at in enumerate(CARE_TIMES):
        if index < 2:
            body = _post(client, at)
            lines[at] = body["activity"]
        else:
            follow = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": at}).get_json()
            lines[at] = follow["activity"]
    return lines


def _check_line(line):
    assert line["text"], "activity text must never be blank"
    assert line["source"], "activity source must never be blank"
    for word in FORBIDDEN:
        assert word not in line["text"], f"false-flavoured word {word!r} in {line['text']!r}"


def test_activity_no_decision_branch(tmp_path, monkeypatch):
    client, investigation_id = _setup_branch(tmp_path, monkeypatch)
    lines = _activities(client, investigation_id)
    assert lines[CARE_TIMES[0]] == {
        "text": "Warm-by plan confirmed (68 F by 7:00 AM); room 69.0 F",
        "source": "event:evt-care-confirmation-request",
    }
    assert lines[CARE_TIMES[1]]["source"] == "computed:readiness"
    assert "68.4 F" in lines[CARE_TIMES[1]]["text"]
    assert "falling" in lines[CARE_TIMES[1]]["text"]
    assert "F an hour" in lines[CARE_TIMES[1]]["text"]
    assert "Readiness at risk" in lines[CARE_TIMES[2]]["text"]
    assert PERMISSION_LINE in lines[CARE_TIMES[2]]["text"]
    assert lines[CARE_TIMES[4]] == {"text": AUTH_LINE, "source": "event:evt-care-caregiver-hvac-authorized"}
    assert lines[CARE_TIMES[5]] == {"text": VISIT_LINE, "source": "event:evt-care-service-visit"}
    assert lines[CARE_TIMES[8]] == {"text": REPORT_LINE, "source": "event:evt-care-hvac-completion-report"}
    assert lines[CARE_TIMES[9]] == {"text": "Warm-by time checked", "source": "computed:arrival_checked"}
    for line in lines.values():
        _check_line(line)


def test_activity_decline_branch(tmp_path, monkeypatch):
    client, investigation_id = _setup_branch(tmp_path, monkeypatch, "decline")
    lines = _activities(client, investigation_id)
    assert PERMISSION_LINE in lines[CARE_TIMES[2]]["text"]
    assert lines[CARE_TIMES[3]]["source"] == "computed:caregiver_declined"
    assert "Caregiver declined HVAC contact at 2:31 AM" in lines[CARE_TIMES[3]]["text"]
    assert "nobody was contacted" in lines[CARE_TIMES[3]]["text"]
    assert AUTH_LINE not in lines[CARE_TIMES[4]]["text"]
    assert lines[CARE_TIMES[5]]["source"] == "computed:telemetry"
    assert "visit" not in lines[CARE_TIMES[5]]["text"].lower()
    assert "restored" not in lines[CARE_TIMES[5]]["text"].lower()
    for at in CARE_TIMES[6:9]:
        assert "completion report" not in lines[at]["text"].lower()
        assert "technician visit" not in lines[at]["text"].lower()
    assert lines[CARE_TIMES[9]]["source"] == "computed:arrival_checked"
    assert lines[CARE_TIMES[9]]["text"].startswith("Warm-by time checked: target missed")
    follow = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": CARE_TIMES[7]}).get_json()
    assert follow["verification"]["stage"] != "goal_verified"
    assert follow["verification"]["stage"] != "warming_observed"
    for line in lines.values():
        _check_line(line)


def test_activity_approve_branch(tmp_path, monkeypatch):
    client, investigation_id = _setup_branch(tmp_path, monkeypatch, "approve")
    lines = _activities(client, investigation_id)
    assert PERMISSION_LINE in lines[CARE_TIMES[2]]["text"]
    assert lines[CARE_TIMES[4]] == {
        "text": "Family caregiver approved HVAC contact at 2:31 AM; HVAC may now be contacted",
        "source": "event:evt-care-caregiver-hvac-authorized",
    }
    assert lines[CARE_TIMES[5]] == {"text": VISIT_LINE, "source": "event:evt-care-service-visit"}
    assert lines[CARE_TIMES[8]] == {"text": REPORT_LINE, "source": "event:evt-care-hvac-completion-report"}
    for line in lines.values():
        _check_line(line)


def test_activity_decision_at_2330(tmp_path, monkeypatch):
    client, approved_id = _setup_branch(tmp_path, monkeypatch, "approve", CARE_TIMES[2])
    approved = _activities(client, approved_id)
    assert approved[CARE_TIMES[4]] == {
        "text": "Family caregiver approved HVAC contact at 23:30; HVAC may now be contacted",
        "source": "event:evt-care-caregiver-hvac-authorized",
    }
    client, declined_id = _setup_branch(tmp_path, monkeypatch, "decline", CARE_TIMES[2])
    declined = _activities(client, declined_id)
    assert declined[CARE_TIMES[2]]["source"] == "computed:caregiver_declined"
    assert "Caregiver declined HVAC contact at 23:30" in declined[CARE_TIMES[2]]["text"]
    assert declined[CARE_TIMES[4]]["source"] == "computed:telemetry"
    assert AUTH_LINE not in declined[CARE_TIMES[4]]["text"]
    for line in list(approved.values()) + list(declined.values()):
        _check_line(line)


def test_activity_rewind_after_decline(tmp_path, monkeypatch):
    client, investigation_id = _setup_branch(tmp_path, monkeypatch, "decline")
    late = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": CARE_TIMES[8]}).get_json()
    assert "completion report" not in late["activity"]["text"].lower()
    rewound = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": CARE_TIMES[2]}).get_json()
    assert PERMISSION_LINE in rewound["activity"]["text"]
    assert "declined" not in rewound["activity"]["text"].lower()
    middle = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": CARE_TIMES[4]}).get_json()
    assert middle["activity"]["source"] == "computed:telemetry"


def test_activity_unit_fallbacks():
    scenario = load_scenario(SCENARIOS_DIR / CARE)
    declined = {"decision": "declined", "actor": "family_caregiver", "decided_at": "2026-01-17T02:31:00-05:00"}
    line = step_activity(scenario, datetime.fromisoformat(CARE_TIMES[4]), None, declined)
    assert line["text"].startswith("No contact made; independent room sensor")
    assert "below the 68" in line["text"]
    assert line["source"] == "computed:telemetry"
    _check_line(line)
    earlier = step_activity(scenario, datetime.fromisoformat(CARE_TIMES[2]), None, declined)
    assert PERMISSION_LINE in earlier["text"]
    assert "declined" not in earlier["text"].lower()
    approved = {"decision": "approved", "actor": "family_caregiver", "decided_at": "2026-01-17T02:31:00-05:00"}
    line = step_activity(scenario, datetime.fromisoformat(CARE_TIMES[4]), None, approved)
    assert line == {
        "text": "Family caregiver approved HVAC contact at 2:31 AM; HVAC may now be contacted",
        "source": "event:evt-care-caregiver-hvac-authorized",
    }


def test_activity_explore_straight_jump(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    for at in CARE_TIMES[:2]:
        body = _post(client, at)
        assert body["follow_up"] is None
        _check_line(body["activity"])
    jump = _post(client, CARE_TIMES[7])
    assert jump["follow_up"] is not None
    assert jump["outcome"] is not None
    _check_line(jump["activity"])
    follow = client.get(f"/api/follow-ups/{jump['investigation_id']}", query_string={"at": CARE_TIMES[7]}).get_json()
    assert follow["verification"]["stage"] == "goal_verified"
    assert follow["outcome"] is not None
    jump = _post(client, CARE_TIMES[8])
    assert jump["follow_up"] is not None
    assert jump["activity"] == {"text": REPORT_LINE, "source": "event:evt-care-hvac-completion-report"}
    jump = _post(client, CARE_TIMES[9])
    assert jump["follow_up"] is not None
    assert jump["activity"] == {"text": "Warm-by time checked", "source": "computed:arrival_checked"}
