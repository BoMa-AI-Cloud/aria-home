from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aria_home.app import create_app
from aria_home.contracts import HomeownerConfirmation, Trip
from aria_home.investigator import build_evidence_pack
from aria_home.outcomes import follow_up_for
from aria_home.readiness import compute_readiness
from aria_home.scenario import context_as_of, load_scenario

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
TZ = timezone(timedelta(hours=-5))


def _at(value):
    return datetime.fromisoformat(value)


def _demo(name="demo_v1"):
    return load_scenario(SCENARIOS / name)


def test_fixtures_carry_explicit_availability_times():
    scenario = _demo()
    assert scenario.trip.known_at == _at("2026-01-16T14:00:00-05:00")
    assert scenario.trip.revision_id == "trip-demo-001-rev1"
    assert scenario.confirmation.revision_id == "trip-demo-001-rev1"
    assert scenario.confirmation.trip_revision == 1
    assert "2026-10-26" in scenario.manifest.scenario_period_note


def test_confirmation_absent_before_confirmed_at_and_present_after():
    scenario = _demo()
    before = _at("2026-01-16T14:15:00-05:00")
    ctx = context_as_of(scenario, before)
    assert ctx.trip is not None
    assert ctx.confirmation is None
    assert ctx.flags["trip_unconfirmed"] is True
    pack = build_evidence_pack(scenario, before)
    assert pack["confirmation"] is None
    assert "confirmation:current" not in pack["evidence_ids"]
    assert pack["metrics"]["target_gap"] is None
    assert pack["readiness"]["status"] == "cannot_tell"
    assert compute_readiness(pack, before)["status"] == "cannot_tell"

    after = _at("2026-01-16T18:00:00-05:00")
    pack = build_evidence_pack(scenario, after)
    assert pack["confirmation"] is not None
    assert "confirmation:current" in pack["evidence_ids"]
    assert pack["metrics"]["target_gap"]["gap"] == -15.9
    assert pack["readiness"]["status"] == "at_risk"


def test_confirmation_without_effect_on_gap_before_confirmed_at_with_samples():
    scenario = _demo()
    scenario.confirmation = HomeownerConfirmation(
        trip_id="trip-demo-001",
        property_id="demo-house",
        target_temp=68,
        target_unit="F",
        notify_homeowner=True,
        manager_authorized=True,
        confirmed_at=_at("2026-01-16T16:45:00-05:00"),
        revision_id="trip-demo-001-rev1",
        trip_revision=1,
    )
    before = build_evidence_pack(scenario, _at("2026-01-16T16:30:00-05:00"))
    assert before["metrics"]["indoor_trend"]["sample_count"] >= 3
    assert before["confirmation"] is None
    assert before["metrics"]["target_gap"] is None
    assert before["readiness"]["status"] == "cannot_tell"
    after = build_evidence_pack(scenario, _at("2026-01-16T17:00:00-05:00"))
    assert after["confirmation"] is not None
    assert after["metrics"]["target_gap"] is not None
    assert after["readiness"]["status"] == "at_risk"


def test_revised_trip_after_confirmation_makes_confirmation_outdated():
    scenario = _demo("demo_revised_v1")
    before_revision = build_evidence_pack(scenario, _at("2026-01-16T16:30:00-05:00"))
    assert before_revision["confirmation"] is not None
    assert before_revision["metrics"]["target_gap"] is not None
    assert before_revision["trip"]["revision_id"] == "trip-demo-001-rev1"

    after = _at("2026-01-16T18:00:00-05:00")
    ctx = context_as_of(scenario, after)
    assert ctx.trip.revision_id == "trip-demo-001-rev2"
    assert ctx.trip.planned_arrival == _at("2026-01-16T20:00:00-05:00")
    assert ctx.confirmation is None
    assert ctx.flags["confirmation_outdated"] is True
    pack = build_evidence_pack(scenario, after)
    assert pack["confirmation"] is None
    assert "confirmation:current" not in pack["evidence_ids"]
    assert pack["metrics"]["target_gap"] is None
    assert pack["readiness"]["status"] == "cannot_tell"
    assert compute_readiness(pack, after)["status"] == "cannot_tell"
    with pytest.raises(ValueError, match="confirmation_outdated"):
        follow_up_for(scenario, "inv-revised", after)


def test_non_material_revision_reuses_confirmation():
    scenario = _demo()
    rev2 = Trip(
        id="trip-demo-001",
        property_id="demo-house",
        title="Owner return (synthetic, title only change)",
        planned_arrival=_at("2026-01-16T18:00:00-05:00"),
        revision=2,
        revision_id="trip-demo-001-rev2",
        known_at=_at("2026-01-16T17:00:00-05:00"),
        cancelled=False,
    )
    scenario.trips = [*scenario.trips, rev2]
    scenario.trip = rev2
    pack = build_evidence_pack(scenario, _at("2026-01-16T18:00:00-05:00"))
    assert pack["trip"]["revision_id"] == "trip-demo-001-rev2"
    assert pack["confirmation"] is not None
    assert pack["metrics"]["target_gap"] is not None
    assert pack["readiness"]["status"] == "at_risk"


def test_cancellation_cannot_tell():
    scenario = _demo("demo_cancelled_v1")
    before = build_evidence_pack(scenario, _at("2026-01-16T16:30:00-05:00"))
    assert before["confirmation"] is not None
    assert before["metrics"]["target_gap"] is not None

    after = _at("2026-01-16T18:00:00-05:00")
    ctx = context_as_of(scenario, after)
    assert ctx.flags["trip_cancelled"] is True
    assert ctx.confirmation is None
    pack = build_evidence_pack(scenario, after)
    assert pack["trip"]["cancelled"] is True
    assert pack["confirmation"] is None
    assert pack["metrics"]["target_gap"] is None
    assert pack["readiness"]["status"] == "cannot_tell"
    with pytest.raises(ValueError, match="trip_cancelled"):
        follow_up_for(scenario, "inv-cancelled", after)


def test_property_mismatch_is_ignored():
    scenario = _demo()
    scenario.confirmation = HomeownerConfirmation(
        trip_id="trip-demo-001",
        property_id="some-other-property",
        target_temp=68,
        target_unit="F",
        notify_homeowner=True,
        manager_authorized=True,
        confirmed_at=_at("2026-01-16T14:30:00-05:00"),
        revision_id="trip-demo-001-rev1",
        trip_revision=1,
    )
    at = _at("2026-01-16T18:00:00-05:00")
    ctx = context_as_of(scenario, at)
    assert ctx.flags["trip_mismatched"] is True
    assert ctx.confirmation is None
    pack = build_evidence_pack(scenario, at)
    assert pack["confirmation"] is None
    assert pack["metrics"]["target_gap"] is None
    assert pack["readiness"]["status"] == "cannot_tell"
    with pytest.raises(ValueError, match="trip_mismatched"):
        follow_up_for(scenario, "inv-mismatch", at)


def test_follow_up_requires_visible_confirmation():
    scenario = _demo()
    with pytest.raises(ValueError, match="trip_unconfirmed"):
        follow_up_for(scenario, "inv-early", _at("2026-01-16T14:15:00-05:00"))
    follow_up = follow_up_for(scenario, "inv-ok", _at("2026-01-16T18:00:00-05:00"))
    assert follow_up.target_temp == 68


def test_endpoints_agree_before_and_after_confirmation(monkeypatch, tmp_path):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "asof.db"))
    monkeypatch.delenv("ARIA_HOME_MODEL_ENABLED", raising=False)
    client = create_app().test_client()

    before = "2026-01-16T14:15:00-05:00"
    metrics = client.get(f"/api/metrics?at={before}").get_json()
    assert metrics["confirmation"] is None
    assert metrics["target_gap"] is None
    assert metrics["computed_readiness"] == "cannot_tell"
    investigation = client.get(f"/api/investigation?at={before}").get_json()
    assert investigation["readiness"]["status"] == "cannot_tell"
    assert investigation["evidence_pack"]["confirmation"] is None
    assert investigation["evidence_pack"]["metrics"]["target_gap"] is None
    created = client.post(f"/api/investigations?scenario=demo_v1&at={before}")
    assert created.status_code == 200
    payload = created.get_json()
    assert payload["computed_readiness"] == "cannot_tell"
    assert payload["follow_up"] is None
    assert payload["flag"] == "trip_unconfirmed"

    after = "2026-01-16T18:00:00-05:00"
    metrics = client.get(f"/api/metrics?at={after}").get_json()
    assert metrics["confirmation"] is not None
    assert metrics["target_gap"]["gap"] == pytest.approx(-15.9)
    assert metrics["computed_readiness"] == "at_risk"
    investigation = client.get(f"/api/investigation?at={after}").get_json()
    assert investigation["readiness"]["status"] == "at_risk"
    assert investigation["evidence_pack"]["metrics"]["target_gap"]["gap"] == -15.9
    created = client.post(f"/api/investigations?scenario=demo_v1&at={after}")
    assert created.status_code == 200
    payload = created.get_json()
    assert payload["computed_readiness"] == "at_risk"
    assert payload["follow_up"] is not None
    follow_up_id = payload["investigation_id"]
    fetched = client.get(f"/api/follow-ups/{follow_up_id}?at=2026-01-16T18:30:00-05:00")
    assert fetched.status_code == 200
    assert fetched.get_json()["follow_up"] is not None


def test_revised_and_cancelled_scenarios_via_investigations_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "asof2.db"))
    monkeypatch.delenv("ARIA_HOME_MODEL_ENABLED", raising=False)
    client = create_app().test_client()
    for name in ("demo_revised_v1", "demo_cancelled_v1"):
        resp = client.post(f"/api/investigations?scenario={name}&at=2026-01-16T18:00:00-05:00")
        assert resp.status_code == 200, name
        payload = resp.get_json()
        assert payload["computed_readiness"] == "cannot_tell", name
        assert payload["follow_up"] is None, name
        assert payload["investigation"]["evidence_pack"]["confirmation"] is None, name
        assert payload["investigation"]["evidence_pack"]["metrics"]["target_gap"] is None, name
