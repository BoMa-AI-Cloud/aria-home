"""The family caregiver approves or declines before ARIA contacts the HVAC company (day11-13)."""
import datetime
from pathlib import Path
from types import SimpleNamespace

from aria_home.contracts import DataMode, EvidenceKind, EvidenceRecord, Provenance, SourceKind
from aria_home.notifications import caregiver_permission_text, create_caregiver_updates, decide_hvac_notification
from aria_home.scenario import load_scenario
from aria_home.store import Store
from aria_home.whatsapp import attempt_caregiver_permission_whatsapp

CONFIGURED_ENV = {"WHATSAPP_TOKEN": "FAKE-TOKEN", "WHATSAPP_PHONE_NUMBER_ID": "111", "WHATSAPP_TEST_RECIPIENT": "15550000000", "ARIA_HOME_WHATSAPP_LIVE": "1"}
CARE = Path(__file__).resolve().parent.parent / "scenarios" / "care_home_v1"
ET = datetime.timezone(datetime.timedelta(hours=-5))


def _aware_now():
    return datetime.datetime.now(datetime.timezone.utc)


def _scenario(events=None):
    return SimpleNamespace(manifest=SimpleNamespace(id="care_home_v1"), events=events or [], records=[])


def _caregiver_alert(store, audience="family_caregiver", kind="caregiver_alert"):
    return store.save_notification(
        investigation_id="inv-1",
        audience=audience,
        kind=kind,
        idempotency_key=f"inv-1:{audience}:{kind}",
        payload={"audience": audience, "kind": kind},
        created_at=_aware_now(),
        delivery="simulated",
        state="simulated_delivered",
    )


class FakePost:
    def __init__(self):
        self.calls = []

    def __call__(self, url, headers, body):
        self.calls.append((url, headers, body))
        return 200, {"messages": [{"id": "wamid.FAKE"}]}


def test_decline_overrides_authorized_event():
    events = [{"kind": "caregiver_hvac_authorized", "available_at": _aware_now()}]
    result = decide_hvac_notification(events=events, scenario=_scenario(events), investigation_id="inv-1", caregiver_decision={"decision": "declined", "decided_at": _aware_now()})
    assert result["allowed"] is False
    assert result["reason"] == "caregiver_declined"


def test_approve_allows_without_events():
    result = decide_hvac_notification(events=[], scenario=_scenario(), investigation_id="inv-1", caregiver_decision={"decision": "approved", "decided_at": _aware_now()})
    assert result["allowed"] is True
    assert result["reason"] is None
    assert set(result["payload"]) <= {"audience", "kind", "property_label", "access_note", "manager_contact_label", "relevant_observations"}


def test_no_decision_no_event_refused():
    result = decide_hvac_notification(events=[], scenario=_scenario(), investigation_id="inv-1")
    assert result["allowed"] is False
    assert result["reason"] == "caregiver_hvac_not_authorized"


def test_record_caregiver_decision_once_only(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    row1, created1 = store.record_caregiver_decision("inv-1", "notif-1", "approved", "family_caregiver", _aware_now())
    assert created1 is True and row1["decision"] == "approved"
    row2, created2 = store.record_caregiver_decision("inv-1", "notif-2", "declined", "family_caregiver", _aware_now())
    assert created2 is False
    assert row2["decision"] == "approved" and row2["notification_id"] == "notif-1"


def test_get_caregiver_decision_hides_future(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    decided_at = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
    store.record_caregiver_decision("inv-1", "notif-1", "approved", "family_caregiver", decided_at)
    assert store.get_caregiver_decision("inv-1", at=decided_at - datetime.timedelta(hours=1)) is None
    assert store.get_caregiver_decision("inv-1", at=decided_at + datetime.timedelta(hours=1)) is not None
    assert store.get_caregiver_decision("inv-1") is not None


def test_permission_text_uses_only_visible_readings():
    scn = load_scenario(CARE)
    text = caregiver_permission_text(scn, datetime.datetime(2026, 1, 17, 2, 31, tzinfo=ET))
    assert text.startswith("ARIA Home (synthetic scenario): your mother's home is cooling (")
    assert "52 F" in text
    assert "16 F below the 68 F target" in text
    assert "thermostat not reporting since 01:30" in text
    assert "temperature unknown" not in text and "since unknown" not in text
    assert text.endswith("May I contact the HVAC company? Approve or decline in ARIA Home.")
    early = caregiver_permission_text(scn, datetime.datetime(2026, 1, 16, 0, 0, tzinfo=ET))
    assert "home is at an unknown temperature (thermostat not reporting)" in early
    assert "below target" not in early


def _unit_record(record_id, source, quantity, value, observed, zone="demo-house/main"):
    return EvidenceRecord(
        id=record_id,
        source=source,
        kind=EvidenceKind.measurement,
        subject=zone,
        quantity=quantity,
        value=value,
        unit="F" if quantity == "indoor_temp" else None,
        observed_at=observed,
        received_at=observed + datetime.timedelta(seconds=60),
        expected_cadence_s=300,
        mode=DataMode.replay,
        provenance=Provenance(fixture_id="unit", version="1"),
    )


def test_permission_text_never_says_cooling_when_trend_rises():
    at = datetime.datetime(2026, 1, 17, 2, 31, tzinfo=ET)
    records = [
        _unit_record(f"room-{i}", SourceKind.room_sensor, "indoor_temp", 60.0 + i * 0.1, at - datetime.timedelta(hours=3) + datetime.timedelta(minutes=5 * i))
        for i in range(36)
    ]
    scn = SimpleNamespace(manifest=SimpleNamespace(id="care_home_v1"), events=[], records=records)
    text = caregiver_permission_text(scn, at)
    assert text.startswith("ARIA Home (synthetic scenario): your mother's home is below target (")
    assert "cooling" not in text
    assert "thermostat not reporting" in text


def test_permission_text_omits_furnace_clause_when_heating():
    at = datetime.datetime(2026, 1, 17, 2, 31, tzinfo=ET)
    records = [
        _unit_record("room-1", SourceKind.room_sensor, "indoor_temp", 60.0, at - datetime.timedelta(minutes=10)),
        _unit_record("tstat-1", SourceKind.thermostat, "indoor_temp", 60.0, at - datetime.timedelta(minutes=5)),
        _unit_record("state-1", SourceKind.thermostat, "hvac_reported_state", "heating", at - datetime.timedelta(minutes=5)),
    ]
    scn = SimpleNamespace(manifest=SimpleNamespace(id="care_home_v1"), events=[], records=records)
    text = caregiver_permission_text(scn, at)
    assert "home is below target (60 F)." in text
    assert "furnace" not in text
    assert "thermostat not reporting" not in text


def test_caregiver_updates_follow_hvac_and_verification(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    hvac = {"state": "simulated_delivered", "created_at": "2026-01-17T02:52:00-05:00", "payload": {"property_label": "demo-house", "access_note": "lockbox"}}
    rows = create_caregiver_updates(store, None, "inv-1", hvac, {"stage": "warming_observed"}, None)
    assert [r["kind"] for r in rows] == ["caregiver_update_hvac_contacted"]
    rows = create_caregiver_updates(store, None, "inv-1", hvac, {"stage": "goal_verified", "goal_verified_at": "2026-01-17T06:21:00-05:00"}, None)
    assert [r["kind"] for r in rows] == ["caregiver_update_hvac_contacted", "caregiver_update_goal_verified"]
    assert len(store.list_notifications("inv-1")) == 2
    assert create_caregiver_updates(store, None, "inv-1", {**hvac, "state": "refused"}, None, None) == []


def test_caregiver_whatsapp_not_configured(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    fake = FakePost()
    result = attempt_caregiver_permission_whatsapp(store, _caregiver_alert(store), "Test permission text", env={}, http_post=fake)
    assert result == {"attempted": False, "reason": "not_configured"}
    assert fake.calls == []


def test_caregiver_whatsapp_configured_once_only(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    notif = _caregiver_alert(store)
    fake = FakePost()
    first = attempt_caregiver_permission_whatsapp(store, notif, "Test permission text", env=CONFIGURED_ENV, http_post=fake)
    assert first["attempted"] is True and first["state"] == "accepted_by_api"
    assert len(fake.calls) == 1
    body = fake.calls[0][2]["text"]["body"]
    assert body.splitlines() == ["ARIA Home test (synthetic scenario)", "To the owner's test number on WhatsApp (stands in for the family caregiver)", "Test permission text"]
    second = attempt_caregiver_permission_whatsapp(store, notif, "Test permission text", env=CONFIGURED_ENV, http_post=fake)
    assert second["reason"] == "already_attempted"
    assert len(fake.calls) == 1
    assert "FAKE-TOKEN" not in str(first) + str(second)


def test_caregiver_whatsapp_wrong_audience(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    fake = FakePost()
    result = attempt_caregiver_permission_whatsapp(store, _caregiver_alert(store, "hvac_company", "hvac_request"), "Test", env=CONFIGURED_ENV, http_post=fake)
    assert result == {"attempted": False, "reason": "not_caregiver_permission"}
    assert fake.calls == []


def test_e2e_reset_empties_every_table(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    store.record_caregiver_decision("inv-1", "notif-1", "approved", "family_caregiver", _aware_now())
    _caregiver_alert(store)
    store.reset_e2e()
    with store._connection() as conn:
        tables = [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()]
        counts = {name: conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in tables}
    assert "caregiver_decisions" in counts
    assert all(count == 0 for count in counts.values()), counts
