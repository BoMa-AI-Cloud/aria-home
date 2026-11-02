"""Activity-line truth across all eleven care_home_v1 steps and all branches.

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
    "2026-01-16T21:41:00-05:00",
    "2026-01-16T22:46:00-05:00",
    "2026-01-16T23:31:00-05:00",
    "2026-01-17T00:21:00-05:00",
    "2026-01-17T00:31:00-05:00",
    "2026-01-17T01:41:00-05:00",
    "2026-01-17T01:51:00-05:00",
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
ON_SITE_LINE = "Technician on site at 23:30, 44 minutes after the caregiver was asked (being on site closes nothing)"
REPORT_LINE = "HVAC completion report (available to ARIA only after verification at 01:40; corroboration only)"
VISIT_LINE = "Technician visit 23:30-00:15 (does not by itself close anything)"


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
    body = _post(client, CARE_TIMES[3])
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
        if index < 3:
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
    assert "holding" in lines[CARE_TIMES[1]]["text"]
    assert "F an hour" not in lines[CARE_TIMES[1]]["text"]
    assert lines[CARE_TIMES[2]]["source"] == "computed:notice"
    assert "Noticed" in lines[CARE_TIMES[2]]["text"]
    assert PERMISSION_LINE not in lines[CARE_TIMES[2]]["text"]
    assert "Readiness at risk" in lines[CARE_TIMES[3]]["text"]
    assert PERMISSION_LINE in lines[CARE_TIMES[3]]["text"]
    assert lines[CARE_TIMES[4]] == {"text": ON_SITE_LINE, "source": "event:evt-care-technician-arrival"}
    assert lines[CARE_TIMES[5]] == {"text": VISIT_LINE, "source": "event:evt-care-service-visit"}
    assert lines[CARE_TIMES[8]] == {"text": REPORT_LINE, "source": "event:evt-care-hvac-completion-report"}
    assert lines[CARE_TIMES[9]] == {"text": "Warm-by time checked", "source": "computed:arrival_checked"}
    for line in lines.values():
        _check_line(line)


def test_activity_decline_branch(tmp_path, monkeypatch):
    client, investigation_id = _setup_branch(tmp_path, monkeypatch, "decline")
    lines = _activities(client, investigation_id)
    assert lines[CARE_TIMES[3]]["source"] == "computed:caregiver_declined"
    assert "Caregiver declined HVAC contact at 10:46 PM" in lines[CARE_TIMES[3]]["text"]
    assert "nobody was contacted" in lines[CARE_TIMES[3]]["text"]
    assert AUTH_LINE not in lines[CARE_TIMES[4]]["text"]
    assert lines[CARE_TIMES[5]]["source"] == "computed:telemetry"
    assert "visit" not in lines[CARE_TIMES[5]]["text"].lower()
    assert "restored" not in lines[CARE_TIMES[5]]["text"].lower()
    for at in CARE_TIMES[4:9]:
        assert "completion report" not in lines[at]["text"].lower()
        assert "technician" not in lines[at]["text"].lower()
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
    assert PERMISSION_LINE in lines[CARE_TIMES[3]]["text"]
    assert lines[CARE_TIMES[4]] == {"text": ON_SITE_LINE, "source": "event:evt-care-technician-arrival"}
    assert lines[CARE_TIMES[5]] == {"text": VISIT_LINE, "source": "event:evt-care-service-visit"}
    assert lines[CARE_TIMES[8]] == {"text": REPORT_LINE, "source": "event:evt-care-hvac-completion-report"}
    for line in lines.values():
        _check_line(line)


def test_activity_rewind_after_decline(tmp_path, monkeypatch):
    client, investigation_id = _setup_branch(tmp_path, monkeypatch, "decline")
    late = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": CARE_TIMES[8]}).get_json()
    assert "completion report" not in late["activity"]["text"].lower()
    rewound = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": CARE_TIMES[3]}).get_json()
    assert rewound["activity"]["source"] == "computed:caregiver_declined"
    middle = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": CARE_TIMES[5]}).get_json()
    assert middle["activity"]["source"] == "computed:telemetry"


def test_activity_unit_fallbacks():
    scenario = load_scenario(SCENARIOS_DIR / CARE)
    declined = {"decision": "declined", "actor": "family_caregiver", "decided_at": "2026-01-16T22:46:00-05:00"}
    line = step_activity(scenario, datetime.fromisoformat(CARE_TIMES[5]), None, declined)
    assert line["text"].startswith("No contact made; independent room sensor")
    assert "below the 68" in line["text"]
    assert line["source"] == "computed:telemetry"
    _check_line(line)
    later_decision = {**declined, "decided_at": "2026-01-16T23:31:00-05:00"}
    earlier = step_activity(scenario, datetime.fromisoformat(CARE_TIMES[3]), None, later_decision)
    assert PERMISSION_LINE in earlier["text"]
    assert "declined" not in earlier["text"].lower()
    approved = {"decision": "approved", "actor": "family_caregiver", "decided_at": "2026-01-16T22:46:00-05:00"}
    line = step_activity(scenario, datetime.fromisoformat("2026-01-16T22:47:00-05:00"), None, approved)
    assert line == {
        "text": "Family caregiver approved HVAC contact at 10:46 PM; HVAC may now be contacted",
        "source": "event:evt-care-caregiver-hvac-authorized",
    }


def test_activity_explore_straight_jump(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    for at in CARE_TIMES[:3]:
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
