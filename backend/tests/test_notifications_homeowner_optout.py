from datetime import datetime, timedelta, timezone
from pathlib import Path

from aria_home.contracts import HomeownerConfirmation
from aria_home.notifications import create_investigation_notifications, decide_notifications
from aria_home.scenario import load_scenario
from aria_home.store import Store

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
TZ = timezone(timedelta(hours=-5))
READINESS = {"status": "cannot_tell", "reasons": ["cold"]}


def _at(value):
    return datetime.fromisoformat(value)


def _ctx(notify, manager=True):
    confirmation = {"manager_authorized": manager}
    if notify != "missing":
        confirmation["notify_homeowner"] = notify
    return {"confirmation": confirmation}


def _homeowner(decisions):
    return next(d for d in decisions if d["audience"] == "homeowner")


def _manager(decisions):
    return next(d for d in decisions if d["audience"] == "property_manager")


def test_opt_out_refused_unit():
    for status in ("cannot_tell", "at_risk", "on_track"):
        d = _homeowner(decide_notifications(readiness={"status": status, "reasons": ["cold"]}, context=_ctx(False), now=_at("2026-01-16T16:31:00-05:00"), investigation_id="inv-1"))
        assert d["allowed"] is False
        assert d["reason"] == "homeowner_opted_out"


def test_opt_in_delivered_unit():
    d = _homeowner(decide_notifications(readiness=READINESS, context=_ctx(True), now=_at("2026-01-16T16:31:00-05:00"), investigation_id="inv-1"))
    assert d["allowed"] is True
    assert d["reason"] is None


def test_missing_or_unknown_preference_refused_unit():
    for context in (None, {}, {"confirmation": None}, _ctx("missing"), _ctx(None), _ctx("yes")):
        d = _homeowner(decide_notifications(readiness=READINESS, context=context, now=_at("2026-01-16T16:31:00-05:00"), investigation_id="inv-1"))
        assert d["allowed"] is False, context
        assert d["reason"] == "homeowner_preference_missing", context


def test_manager_unaffected_by_homeowner_preference_unit():
    for notify, homeowner_allowed in ((False, False), (True, True), ("missing", False)):
        decisions = decide_notifications(readiness=READINESS, context=_ctx(notify, manager=True), now=_at("2026-01-16T16:31:00-05:00"), investigation_id="inv-1")
        assert _homeowner(decisions)["allowed"] is homeowner_allowed
        assert _manager(decisions)["allowed"] is True
        decisions = decide_notifications(readiness=READINESS, context=_ctx(notify, manager=False), now=_at("2026-01-16T16:31:00-05:00"), investigation_id="inv-1")
        assert _manager(decisions)["allowed"] is False
        assert _manager(decisions)["reason"] == "manager_not_authorized"


def _confirmation(notify, confirmed_at, manager=True):
    return HomeownerConfirmation(
        trip_id="trip-demo-001",
        property_id="demo-house",
        target_temp=68,
        target_unit="F",
        notify_homeowner=notify,
        manager_authorized=manager,
        confirmed_at=_at(confirmed_at),
        revision_id="trip-demo-001-rev1",
        trip_revision=1,
        trip_revision_id="trip-demo-001-rev1",
    )


def _persisted_homeowner(tmp_path, scenario, inv_id, at):
    store = Store(tmp_path / "n.db")
    rows = create_investigation_notifications(store, scenario, inv_id, None, READINESS, at)
    return next(r for r in rows if r["audience"] == "homeowner"), next((r for r in rows if r["audience"] == "property_manager"), None)


def test_opt_out_persisted_refused_never_delivered(tmp_path):
    scenario = load_scenario(SCENARIOS / "demo_v1")
    opted_out = _confirmation(False, "2026-01-16T14:30:00-05:00")
    scenario.confirmation = opted_out
    scenario.confirmations = [opted_out]
    row, manager = _persisted_homeowner(tmp_path, scenario, "inv-out", _at("2026-01-16T15:00:00-05:00"))
    assert row["state"] == "refused"
    assert row["refusal_reason"] == "homeowner_opted_out"
    assert row["reason"] == "homeowner_opted_out"
    assert manager is not None and manager["state"] == "simulated_delivered"


def test_opt_in_persisted_delivered(tmp_path):
    scenario = load_scenario(SCENARIOS / "demo_v1")
    row, _ = _persisted_homeowner(tmp_path, scenario, "inv-in", _at("2026-01-16T15:00:00-05:00"))
    assert row["state"] == "simulated_delivered"


def test_missing_preference_persisted_refused(tmp_path):
    scenario = load_scenario(SCENARIOS / "demo_v1")
    row, manager = _persisted_homeowner(tmp_path, scenario, "inv-early", _at("2026-01-16T14:15:00-05:00"))
    assert row["state"] == "refused"
    assert row["refusal_reason"] == "homeowner_preference_missing"
    assert manager is not None and manager["state"] == "refused"
    assert manager["refusal_reason"] == "manager_not_authorized"


def test_preference_changed_by_later_confirmation_revision_as_of(tmp_path):
    scenario = load_scenario(SCENARIOS / "demo_v1")
    early = _confirmation(True, "2026-01-16T14:30:00-05:00")
    later = _confirmation(False, "2026-01-16T15:30:00-05:00")
    scenario.confirmations = [early, later]
    scenario.confirmation = later
    store = Store(tmp_path / "n.db")
    before = create_investigation_notifications(store, scenario, "inv-before", None, READINESS, _at("2026-01-16T15:00:00-05:00"))
    after = create_investigation_notifications(store, scenario, "inv-after", None, READINESS, _at("2026-01-16T16:00:00-05:00"))
    assert next(r for r in before if r["audience"] == "homeowner")["state"] == "simulated_delivered"
    refused = next(r for r in after if r["audience"] == "homeowner")
    assert refused["state"] == "refused"
    assert refused["refusal_reason"] == "homeowner_opted_out"
    assert next(r for r in after if r["audience"] == "property_manager")["state"] == "simulated_delivered"
