import json
from pathlib import Path

from aria_home.app import create_app
from aria_home.notifications import ALLOWLISTS
from aria_home.scenario import load_scenario

AUDIT = Path(__file__).resolve().parent.parent.parent / "docs" / "fields-audit.json"
SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"


def test_fields_audit_matches_code_at_1652(tmp_path, monkeypatch):
    data = json.loads(AUDIT.read_text(encoding="utf-8"))
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "audit.db"))
    client = create_app().test_client()
    inv = client.post("/api/investigations?scenario=demo_video_v1&at=2026-01-16T16:31:00-05:00").get_json()["investigation_id"]
    client.get(f"/api/follow-ups/{inv}?at=2026-01-16T16:31:00-05:00")
    client.get(f"/api/follow-ups/{inv}?at=2026-01-16T16:52:00-05:00")
    rows = client.get(f"/api/notifications?investigation_id={inv}").get_json()["notifications"]
    hvac = next(r for r in rows if r["audience"] == "hvac_company" and r["state"] == "simulated_delivered")
    scenario = load_scenario(SCENARIOS / "demo_video_v1")
    auth = next(e for e in scenario.events if e.kind == "manager_hvac_authorized")
    union = set().union(*ALLOWLISTS.values())
    assert data["scenario"] == "demo_video_v1"
    assert data["audience"] == "hvac_company"
    assert data["fields_sent"] == sorted(hvac["payload"].keys())
    assert data["field_values"] == hvac["payload"]
    assert data["fields_refused"] == sorted(union - set(ALLOWLISTS["hvac_company"]))
    assert data["authorising_event"] == {"id": auth.id, "kind": auth.kind, "available_at": auth.available_at.isoformat(), "event_time": auth.event_time.isoformat()}
    assert data["simulated"] is (hvac["delivery"] == "simulated" and auth.simulated is True)
    assert data["delivery"] == hvac["delivery"]
    assert data["state"] == hvac["state"]
    assert data["notification_created_at"] == hvac["created_at"]
    refused = [r for r in rows if r["state"] == "refused"]
    assert data["refused_notifications"] == [{"audience": r["audience"], "kind": r["kind"], "refusal_reason": r["refusal_reason"]} for r in refused]
