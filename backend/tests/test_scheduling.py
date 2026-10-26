import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aria_home.app import create_app
from aria_home.investigator import build_evidence_pack, investigate, validate
from aria_home.outcomes import FollowUp
from aria_home.provider import MockProvider
from aria_home.scenario import load_scenario
from aria_home.scheduling import compute_follow_up_schedule, compute_next_check_at
from aria_home.store import Store
from test_investigator import FakeProvider, _valid_json

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
TZ = timezone(timedelta(hours=-5))
AT = datetime(2026, 1, 16, 18, 0, tzinfo=TZ)
DEADLINE = datetime(2026, 1, 16, 20, 0, tzinfo=TZ)


def test_computed_next_check_uses_cadence_and_window():
    assert compute_next_check_at(AT, deadline=DEADLINE, cadence_s=1800) == AT + timedelta(minutes=30)
    assert compute_next_check_at(AT, deadline=DEADLINE, cadence_s=60) == AT + timedelta(minutes=15)
    assert compute_next_check_at(AT, deadline=DEADLINE, cadence_s=999999) == DEADLINE
    assert compute_next_check_at(AT, deadline=AT + timedelta(days=7)) == AT + timedelta(minutes=30)


@pytest.mark.parametrize("bad", [
    AT - timedelta(hours=1),
    AT,
    AT + timedelta(minutes=5),
    AT + timedelta(hours=25),
    DEADLINE + timedelta(minutes=1),
])
def test_schedule_rejects_invalid_model_times_and_uses_computed(bad):
    s = compute_follow_up_schedule(AT, deadline=DEADLINE, cadence_s=1800, model_when=bad)
    assert s["model_time_valid"] is False
    assert s["model_time_rejected"] is True
    assert s["next_check_at"] == AT + timedelta(minutes=30)


def test_schedule_rejects_naive_model_time():
    s = compute_follow_up_schedule(AT, deadline=DEADLINE, model_when=datetime(2026, 1, 16, 18, 30))
    assert s["model_time_valid"] is False
    assert s["next_check_at"] == AT + timedelta(minutes=30)
    with pytest.raises(ValueError):
        compute_follow_up_schedule(datetime(2026, 1, 16, 18, 0), deadline=DEADLINE)


def test_deadline_passed_schedules_no_future_check():
    s = compute_follow_up_schedule(AT, deadline=AT - timedelta(hours=1))
    assert s["status"] == "deadline_passed"
    assert s["flag"] == "deadline_passed"
    assert s["deadline_passed"] is True
    assert s["next_check_at"] is None
    s2 = compute_follow_up_schedule(AT, arrival=AT - timedelta(hours=3))
    assert s2["deadline_passed"] is True
    assert s2["next_check_at"] is None


@pytest.mark.parametrize("when", [
    "2026-01-16T17:00:00-05:00",
    "2026-01-16T18:00:00-05:00",
    "2026-01-16T18:30:00",
    "2026-01-17T19:00:00-05:00",
])
def test_investigator_replaces_invalid_model_times(when):
    scenario = load_scenario(SCENARIOS / "demo_v1")
    data = json.loads(_valid_json(AT))
    data["follow_up"]["when"] = when
    pack = build_evidence_pack(scenario, AT)
    assert validate(data, pack)
    result = investigate(scenario, AT, FakeProvider(json.dumps(data)))
    assert result.status == "ok", result.reasons
    assert result.output.follow_up.when == AT + timedelta(minutes=30)
    assert result.output.follow_up.next_check_at == AT + timedelta(minutes=30)
    assert result.output.follow_up.when.tzinfo is not None
    assert result.output.follow_up.deadline_passed is False


def test_store_rejects_invalid_follow_up_times(tmp_path):
    store = Store(tmp_path / "a.db")
    base = dict(investigation_id="inv-1", created_at=AT, target_temp=68.0, target_unit="F", deadline=DEADLINE)
    with pytest.raises(ValueError):
        FollowUp(**{**base, "deadline": AT - timedelta(hours=1)})
    with pytest.raises(ValueError):
        FollowUp(**{**base, "deadline": datetime(2026, 1, 16, 20, 0)})
    with pytest.raises(ValueError):
        FollowUp(**{**base, "next_check_at": AT - timedelta(hours=1)})
    with pytest.raises(ValueError):
        FollowUp(**{**base, "next_check_at": datetime(2026, 1, 16, 18, 30)})
    with pytest.raises(ValueError):
        store.save_follow_up({**base, "next_check_at": (AT + timedelta(days=2)).isoformat()})
    assert store.get_follow_up("inv-1") is None
    store.close()


def test_post_persists_only_valid_time(tmp_path, monkeypatch):
    db = tmp_path / "api.db"
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(db))
    client = create_app().test_client()
    resp = client.post("/api/investigations?scenario=demo_v1&at=2026-01-16T18:00:00-05:00")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["deadline_passed"] is False
    nxt = datetime.fromisoformat(payload["follow_up"]["next_check_at"])
    created = datetime.fromisoformat(payload["follow_up"]["created_at"])
    deadline = datetime.fromisoformat(payload["follow_up"]["deadline"])
    assert nxt.tzinfo is not None and nxt.utcoffset() is not None
    assert created + timedelta(minutes=15) <= nxt <= min(deadline, created + timedelta(hours=24))
    assert payload["follow_up"]["when"] == payload["follow_up"]["next_check_at"]
    conn = sqlite3.connect(db)
    row = conn.execute("SELECT next_check_at FROM follow_ups").fetchone()
    conn.close()
    assert datetime.fromisoformat(row[0]) == nxt


def test_post_deadline_passed(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    client = create_app().test_client()
    resp = client.post("/api/investigations?scenario=demo_v1&at=2026-01-16T21:00:00-05:00")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["deadline_passed"] is True
    assert payload["schedule_status"] == "deadline_passed"
    assert payload["follow_up"] is None
    assert payload["next_check_at"] is None
