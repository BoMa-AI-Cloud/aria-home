"""Flask application factory for the ARIA Home backend."""
import os
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, request

from aria_home.contracts import SourceKind
from aria_home.eligibility import eligible_records
from aria_home.evidence import source_status
from aria_home.metrics import NOISE_FLOOR_W, circuit_activity, target_gap, temperature_trend
from aria_home.investigator import Investigation, build_evidence_pack, inference_identity, investigate
from aria_home.outcomes import evaluate_outcome, follow_up_for
from aria_home.store import Store
from aria_home.power_context import power_context
from aria_home.provider import ProviderConfig, get_provider
from aria_home.scenario import context_as_of, events_as_of, load_scenario, visible_records
from aria_home.readiness import compute_readiness
from aria_home.scheduling import compute_follow_up_schedule
from aria_home.verification import verify_recovery
from aria_home.notifications import create_hvac_notification, create_investigation_notifications

SCENARIO_PATH = Path(__file__).resolve().parent.parent / "scenarios" / "demo_v1"


def create_app():
    app = Flask(__name__)
    scenario = load_scenario(SCENARIO_PATH)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "aria-home-backend", "data_mode": "synthetic", "scenario": scenario.manifest.id, "at": (scenario.manifest.start + timedelta(hours=3)).isoformat(), "timezone": scenario.manifest.timezone})

    @app.get("/api/evaluation/offline")
    def evaluation_offline():
        import json

        path = Path(__file__).resolve().parent.parent / "eval" / "results-offline.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload.setdefault("scenario", scenario.manifest.id)
            payload.setdefault("at", (scenario.manifest.start + timedelta(hours=3)).isoformat())
            payload.setdefault("timezone", scenario.manifest.timezone)
        return jsonify(payload)

    @app.get("/api/sources")
    def sources():
        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "data_mode": "synthetic", "scenario": request.args.get("scenario"), "at": request.args.get("at"), "timezone": scenario.manifest.timezone}), 404
        raw_at = request.args.get("at")
        if raw_at:
            try:
                at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "at must be an ISO 8601 datetime", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
            if at.tzinfo is None or at.utcoffset() is None:
                return jsonify({"error": "at must be timezone-aware", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
        else:
            at = scn.manifest.start + timedelta(hours=3)

        visible = visible_records(scn.records, at)
        has_room_sensor = any(r.source is SourceKind.room_sensor for r in scn.records)
        statuses = [
            source_status(source, visible, at, mode=scn.manifest.mode)
            for source in SourceKind
            if source is not SourceKind.room_sensor or has_room_sensor
        ]
        return jsonify(
            {
                "data_mode": scn.manifest.mode.value,
                "scenario": scn.manifest.id,
                "at": at.isoformat(),
                "timezone": scn.manifest.timezone,
                "sources": [s.model_dump(mode="json") for s in statuses],
            }
        )

    @app.get("/api/provider")
    def provider():
        try:
            config = ProviderConfig.from_env(os.environ)
            selected = get_provider(config)
        except ValueError as exc:
            return jsonify({"error": str(exc), "scenario": scenario.manifest.id, "at": (scenario.manifest.start + timedelta(hours=3)).isoformat(), "timezone": scenario.manifest.timezone}), 400
        missing = config.missing_settings() if config.enabled else None
        return jsonify(
            {
                "mode": selected.mode,
                "model_id": config.model_id,
                "enabled": config.enabled,
                "key_present": bool(config.api_key),
                "configured": config.configured,
                "config_error": missing or None,
                "scenario": scenario.manifest.id,
                "at": (scenario.manifest.start + timedelta(hours=3)).isoformat(),
                "timezone": scenario.manifest.timezone,
            }
        )

    @app.get("/api/metrics")
    def metrics():
        from datetime import datetime as _datetime

        def _jsonable(value):
            if isinstance(value, _datetime):
                return value.isoformat()
            if isinstance(value, dict):
                return {k: _jsonable(v) for k, v in value.items()}
            if isinstance(value, list):
                return [_jsonable(v) for v in value]
            return value

        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "scenario": request.args.get("scenario"), "at": request.args.get("at"), "timezone": scenario.manifest.timezone}), 404
        raw_at = request.args.get("at")
        if raw_at:
            try:
                at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "at must be an ISO 8601 datetime", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
            if at.tzinfo is None or at.utcoffset() is None:
                return jsonify({"error": "at must be timezone-aware", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
        else:
            at = scn.manifest.start + timedelta(hours=3)

        start = at - timedelta(hours=3)
        ctx = context_as_of(scn, at)
        visible = visible_records(scn.records, at)
        zones = sorted({r.subject for r in eligible_records(visible, "indoor_temp", now=at, require_value=False)})
        zone = zones[0] if zones else "demo-cabin/main"
        trend = temperature_trend(visible, zone, start, at, at)
        gap = None
        if ctx.confirmation is not None:
            gap = target_gap(trend, ctx.confirmation.target_temp, ctx.confirmation.target_unit)
        circuit_ids = sorted(
            {
                (r.binding.circuit_id if r.binding else None) or r.subject
                for r in eligible_records(visible, "circuit_power", now=at, require_value=False)
            }
        )
        circuits = {cid: _jsonable(circuit_activity(visible, cid, start, at, at)) for cid in circuit_ids}
        statuses = [
            source_status(source, visible, at, mode=scn.manifest.mode)
            for source in SourceKind
        ]
        trip_payload = ctx.trip.model_dump(mode="json") if ctx.trip is not None else None
        confirmation_payload = ctx.confirmation.model_dump(mode="json") if ctx.confirmation is not None else None
        readiness_pack = {
            "at": at.isoformat(),
            "trip": trip_payload,
            "confirmation": confirmation_payload,
            "source_statuses": _jsonable(statuses),
            "metrics": {"indoor_trend": _jsonable(trend), "target_gap": _jsonable(gap)},
            "readiness_flags": dict(ctx.flags),
        }
        readiness = compute_readiness(readiness_pack, at, flags=dict(ctx.flags))
        return jsonify(
            {
                "data_mode": scn.manifest.mode.value,
                "computed_by": "deterministic code",
                "scenario": scn.manifest.id,
                "at": at.isoformat(),
                "timezone": scn.manifest.timezone,
                "zone": zone,
                "window": {"start": start.isoformat(), "end": at.isoformat()},
                "indoor_trend": _jsonable(trend),
                "target_gap": _jsonable(gap),
                "circuits": circuits,
                "trip": trip_payload,
                "confirmation": confirmation_payload,
                "readiness_flags": dict(ctx.flags),
                "flags": dict(ctx.flags),
                "context_flags": dict(ctx.flags),
                "readiness": _jsonable(dict(readiness)),
                "computed_readiness": readiness["status"],
            }
        )

    @app.get("/api/power-context")
    def power_context_endpoint():
        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "scenario": request.args.get("scenario"), "at": request.args.get("at"), "timezone": scenario.manifest.timezone}), 404
        raw_at = request.args.get("at")
        if raw_at:
            try:
                at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "at must be an ISO 8601 datetime", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
            if at.tzinfo is None or at.utcoffset() is None:
                return jsonify({"error": "at must be timezone-aware", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
        else:
            at = scn.manifest.start + timedelta(hours=3)
        start = at - timedelta(hours=3)
        visible = visible_records(scn.records, at)
        result = power_context(visible, start, at, NOISE_FLOOR_W)
        payload = result.model_dump(mode="json")
        payload.update(
            {
                "data_mode": scn.manifest.mode.value,
                "computed_by": "deterministic code",
                "scenario": scn.manifest.id,
                "at": at.isoformat(),
                "timezone": scn.manifest.timezone,
                "window": {"start": start.isoformat(), "end": at.isoformat()},
            }
        )
        return jsonify(payload)

    @app.get("/api/investigation")
    def investigation():
        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "scenario": request.args.get("scenario"), "at": request.args.get("at"), "timezone": scenario.manifest.timezone}), 404
        raw_at = request.args.get("at")
        if raw_at:
            try:
                at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "at must be an ISO 8601 datetime", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
            if at.tzinfo is None or at.utcoffset() is None:
                return jsonify({"error": "at must be timezone-aware", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
        else:
            at = scn.manifest.start + timedelta(hours=3)
        try:
            provider = get_provider()
        except ValueError as exc:
            return jsonify({"error": str(exc), "scenario": scn.manifest.id, "at": at.isoformat(), "timezone": scn.manifest.timezone}), 400
        result = investigate(scn, at, provider)
        payload = result.model_dump(mode="json")
        payload["data_mode"] = "synthetic"
        payload["scenario"] = scn.manifest.id
        payload["at"] = at.isoformat()
        payload["timezone"] = scn.manifest.timezone
        payload["evaluated_at"] = at.isoformat()
        payload["readiness"] = result.evidence_pack.get("readiness") if result.evidence_pack else None
        payload["computed_readiness"] = payload["readiness"].get("status") if isinstance(payload.get("readiness"), dict) else None
        return jsonify(payload)

    _store = None
    _scenarios = {}

    def _get_store():
        nonlocal _store
        if _store is None:
            _store = Store()
        return _store

    def _load_named_scenario(name):
        import re

        scenario_name = name or "demo_v1"
        if not re.fullmatch(r"[A-Za-z0-9_-]+", scenario_name):
            return None
        if scenario_name not in _scenarios:
            if scenario_name == scenario.manifest.id:
                _scenarios[scenario_name] = scenario
            else:
                path = SCENARIO_PATH.parent / scenario_name
                if not (path / "manifest.json").is_file():
                    return None
                _scenarios[scenario_name] = load_scenario(path)
        return _scenarios[scenario_name]

    def _parse_at(raw_at, default):
        if not raw_at:
            return default, None
        try:
            at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
        except ValueError:
            return None, (jsonify({"error": "at must be an ISO 8601 datetime", "data_mode": "synthetic"}), 400)
        if at.tzinfo is None or at.utcoffset() is None:
            return None, (jsonify({"error": "at must be timezone-aware", "data_mode": "synthetic"}), 400)
        return at, None

    def _notification_api(row):
        if row is None:
            return None
        item = {k: v for k, v in row.items() if k != "payload_json"}
        return item

    @app.get("/api/context")
    def context_endpoint():
        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "data_mode": "synthetic", "scenario": request.args.get("scenario"), "at": request.args.get("at"), "timezone": scenario.manifest.timezone}), 404
        at, error = _parse_at(request.args.get("at"), scn.manifest.start + timedelta(hours=3))
        if error:
            return error
        ctx = context_as_of(scn, at)
        flags = dict(ctx.flags)
        base = {"data_mode": scn.manifest.mode.value, "scenario": scn.manifest.id, "at": at.isoformat(), "timezone": scn.manifest.timezone, "flags": flags, "context_flags": dict(flags), "readiness_flags": dict(flags)}
        trip_payload = ctx.trip.model_dump(mode="json") if ctx.trip is not None else None
        if ctx.confirmation is None:
            if flags.get("trip_cancelled"):
                reason, reason_in_words = "trip_cancelled", "Trip cancelled"
            elif flags.get("confirmation_outdated"):
                reason, reason_in_words = "confirmation_outdated", "Confirmation outdated for the current trip"
            elif flags.get("trip_mismatched"):
                reason, reason_in_words = "trip_mismatched", "Trip and confirmation do not match"
            else:
                reason, reason_in_words = "trip_unconfirmed", "Not yet confirmed"
            return jsonify({**base, "confirmed": False, "reason": reason, "reason_in_words": reason_in_words, "confirmation": None, "confirmed_at": None, "revision_id": None, "current_trip_revision_id": ctx.trip.revision_id if ctx.trip is not None else None})
        confirmation = ctx.confirmation
        trip = ctx.trip
        arrival_plan = dict(getattr(scn, "arrival_plan", None) or {}) or None
        allowances = []
        if arrival_plan:
            if arrival_plan.get("airport_exit_baggage_allowance_min") is not None:
                allowances.append({"kind": "airport_exit_baggage", "minutes": arrival_plan["airport_exit_baggage_allowance_min"], "label": arrival_plan.get("airport_exit_baggage_label") or f"labeled allowance: {arrival_plan['airport_exit_baggage_allowance_min']} min airport-exit/baggage"})
            if arrival_plan.get("driving_allowance_min") is not None:
                allowances.append({"kind": "driving", "minutes": arrival_plan["driving_allowance_min"], "label": arrival_plan.get("driving_label") or f"labeled allowance: {arrival_plan['driving_allowance_min']} min driving"})
        revision_id = confirmation.revision_id or confirmation.trip_revision_id or (trip.revision_id if trip is not None else None)
        property_label = trip.property_id if trip is not None else confirmation.property_id
        return jsonify({**base, "confirmed": True, "reason": None, "property_label": property_label, "property_id": property_label, "property": property_label, "planned_arrival": trip.planned_arrival.isoformat() if trip is not None else None, "arrival_plan": arrival_plan, "landing": arrival_plan.get("landing") if arrival_plan else None, "allowances": allowances, "arrival_allowances": allowances, "arrival_estimates_note": "Arrival times and allowances are scenario estimates, not live travel claims", "estimates_note": "Scenario estimates, not live travel claims", "target_temp": confirmation.target_temp, "target_unit": confirmation.target_unit, "target_temperature": f"{confirmation.target_temp:g} {confirmation.target_unit}", "notify_homeowner": confirmation.notify_homeowner, "homeowner_notification_preference": confirmation.notify_homeowner, "homeowner_notification": confirmation.notify_homeowner, "manager_authorized": confirmation.manager_authorized, "manager_coordination_permission": confirmation.manager_authorized, "manager_coordination": "allowed" if confirmation.manager_authorized else "not allowed", "confirmed_at": confirmation.confirmed_at.isoformat(), "revision_id": revision_id, "trip_revision_id": revision_id, "confirmation_revision_id": revision_id, "trip_revision": confirmation.trip_revision, "trip": trip_payload, "confirmation": confirmation.model_dump(mode="json")})

    def _follow_up_payload(store, investigation_id, at=None, outcome=None):
        follow_up = store.get_follow_up(investigation_id)
        row = store.get_follow_up_row(investigation_id)
        if follow_up is None:
            return None
        payload = follow_up.model_dump(mode="json")
        if at is not None and outcome is not None:
            status = outcome.status.value if hasattr(outcome.status, "value") else outcome.status
            payload.update({"target": row["target"], "last_status": status, "status": status, "last_evaluated_at": at.isoformat() if hasattr(at, "isoformat") else str(at), "supporting_ids": list(outcome.supporting_ids), "next_check_at": row.get("next_check_at") or payload.get("next_check_at"), "when": row.get("next_check_at") or payload.get("next_check_at"), "schedule_status": row.get("schedule_status") or payload.get("schedule_status"), "deadline_passed": row.get("deadline_passed", payload.get("deadline_passed"))})
            return payload
        payload.update({"target": row["target"], "last_status": row["last_status"], "status": row["last_status"], "last_evaluated_at": row["last_evaluated_at"], "supporting_ids": row["supporting_ids"], "next_check_at": row.get("next_check_at") or payload.get("next_check_at"), "when": row.get("next_check_at") or payload.get("next_check_at"), "schedule_status": row.get("schedule_status") or payload.get("schedule_status"), "deadline_passed": row.get("deadline_passed", payload.get("deadline_passed"))})
        return payload

    @app.post("/api/investigations")
    def create_investigation():
        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "data_mode": "synthetic"}), 404
        at, error = _parse_at(request.args.get("at"), scn.manifest.start + timedelta(hours=3))
        if error:
            return error
        try:
            provider = get_provider()
        except ValueError as exc:
            return jsonify({"error": str(exc), "data_mode": "synthetic"}), 400
        pack = build_evidence_pack(scn, at)
        identity = inference_identity(scn, at, pack=pack)
        investigation_id = identity["investigation_id"]
        store = _get_store()
        retry = str(request.args.get("retry") or "").lower() in ("1", "true", "yes")
        claimed, claim_row = store.claim_inference(identity, retry=retry)
        deduplicated = False
        if not claimed:
            if claim_row is None or claim_row["state"] == "pending":
                return jsonify({"data_mode": "synthetic", "status": "pending", "investigation_status": "pending", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "identity": {k: identity[k] for k in ("scenario_id", "scenario_fixture_version", "evaluated_at_utc", "input_revision", "prompt_version", "readiness_policy_version")}, "identity_key": identity["identity_key"]}), 202
            if claim_row["result"] is None:
                return jsonify({"data_mode": "synthetic", "status": "pending", "investigation_status": "pending", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "identity_key": identity["identity_key"]}), 202
            result = Investigation.model_validate(claim_row["result"])
            deduplicated = True
        else:
            try:
                result = investigate(scn, at, provider)
            except Exception as exc:
                result = Investigation(status="unavailable", reasons=[f"provider error: {exc}"], prompt_version=identity["prompt_version"], evidence_pack=pack)
            store.complete_inference(identity["identity_key"], result.model_dump(mode="json"), "completed" if result.status == "ok" else "failed")
        store.save_investigation(result, investigation_id=investigation_id, scenario=scn.manifest.id, evaluated_at=at)
        _readiness_for_notif = result.evidence_pack.get("readiness") if result.evidence_pack else None
        notif_rows = [_notification_api(r) for r in create_investigation_notifications(store, scn, investigation_id, result, _readiness_for_notif, at)]
        ctx = context_as_of(scn, at)
        arrival = ctx.trip.planned_arrival if ctx.trip else None
        cadence_s = next((r.expected_cadence_s for r in scn.records if r.quantity == "indoor_temp" and r.expected_cadence_s is not None), None)
        model_when = None
        if result.output and result.output.follow_up:
            model_when = result.output.follow_up.next_check_at or result.output.follow_up.when
        schedule = compute_follow_up_schedule(at, arrival=arrival, cadence_s=cadence_s, model_when=model_when)
        schedule_payload = {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in schedule.items()}
        investigation_payload = result.model_dump(mode="json")
        readiness = result.evidence_pack.get("readiness") if result.evidence_pack else None
        computed_readiness = readiness.get("status") if isinstance(readiness, dict) else None
        investigation_payload.update({"id": investigation_id, "investigation_id": investigation_id, "scenario": scn.manifest.id, "evaluated_at": at.isoformat(), "readiness": readiness, "computed_readiness": computed_readiness})
        if schedule["deadline_passed"]:
            return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "status": "deadline_passed", "investigation_status": result.status, "readiness": readiness, "computed_readiness": computed_readiness, "investigation": investigation_payload, "follow_up": None, "follow_up_schedule": schedule_payload, "schedule": schedule_payload, "schedule_status": "deadline_passed", "flag": "deadline_passed", "deadline_passed": True, "next_check_at": None, "outcome": None, "notifications": notif_rows, "deduplicated": deduplicated, "identity_key": identity["identity_key"], "input_revision": identity["input_revision"]})
        try:
            follow_up = follow_up_for(scn, investigation_id, at, cadence_s=cadence_s)
        except ValueError as exc:
            if "deadline_passed" in str(exc):
                return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "status": "deadline_passed", "investigation_status": result.status, "readiness": readiness, "computed_readiness": computed_readiness, "investigation": investigation_payload, "follow_up": None, "follow_up_schedule": schedule_payload, "schedule": schedule_payload, "schedule_status": "deadline_passed", "flag": "deadline_passed", "deadline_passed": True, "next_check_at": None, "outcome": None, "notifications": notif_rows, "deduplicated": deduplicated, "identity_key": identity["identity_key"], "input_revision": identity["input_revision"]})
            if any(token in str(exc) for token in ("trip_cancelled", "trip_unconfirmed", "trip_mismatched", "confirmation_outdated", "no homeowner confirmation", "no trip visible")):
                primary = next((name for name in ("trip_cancelled", "confirmation_outdated", "trip_mismatched", "trip_unconfirmed") if ctx.flags.get(name)), "trip_unconfirmed")
                not_scheduled = {**schedule_payload, "status": "not_scheduled", "schedule_status": "not_scheduled", "next_check_at": None, "when": None}
                return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "status": "cannot_tell", "investigation_status": result.status, "readiness": readiness, "computed_readiness": computed_readiness, "investigation": investigation_payload, "follow_up": None, "follow_up_schedule": not_scheduled, "schedule": not_scheduled, "schedule_status": "not_scheduled", "flag": primary, "flags": dict(ctx.flags), "readiness_flags": dict(ctx.flags), "context_flags": dict(ctx.flags), "deadline_passed": False, "next_check_at": None, "outcome": None, "error": str(exc), "notifications": notif_rows, "deduplicated": deduplicated, "identity_key": identity["identity_key"], "input_revision": identity["input_revision"]})
            return jsonify({"error": str(exc), "data_mode": "synthetic"}), 400
        if follow_up.next_check_at is None or follow_up.next_check_at.tzinfo is None or follow_up.next_check_at <= follow_up.created_at:
            return jsonify({"error": "invalid follow-up schedule", "data_mode": "synthetic"}), 400
        try:
            outcome = evaluate_outcome(follow_up, scn.records, at)
            store.save_follow_up(follow_up, outcome=outcome)
        except ValueError as exc:
            return jsonify({"error": str(exc), "data_mode": "synthetic"}), 400
        return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "status": result.status, "readiness": readiness, "computed_readiness": computed_readiness, "investigation": investigation_payload, "follow_up": _follow_up_payload(store, investigation_id), "follow_up_schedule": schedule_payload, "schedule": schedule_payload, "schedule_status": schedule["status"], "deadline_passed": False, "next_check_at": schedule_payload["next_check_at"], "outcome": outcome.model_dump(mode="json"), "notifications": notif_rows, "deduplicated": deduplicated, "identity_key": identity["identity_key"], "input_revision": identity["input_revision"]})

    @app.get("/api/events")
    def events_endpoint():
        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "data_mode": "synthetic"}), 404
        at, error = _parse_at(request.args.get("at"), scn.manifest.start + timedelta(hours=3))
        if error:
            return error
        return jsonify(
            {
                "data_mode": "synthetic",
                "scenario": scn.manifest.id,
                "at": at.isoformat(),
                "events": [event.model_dump(mode="json") for event in events_as_of(scn, at)],
            }
        )

    @app.get("/api/follow-ups/<investigation_id>")
    def get_follow_up_endpoint(investigation_id):
        store = _get_store()
        follow_up = store.get_follow_up(investigation_id)
        if follow_up is None:
            return jsonify({"error": "follow-up not found", "data_mode": "synthetic"}), 404
        at, error = _parse_at(request.args.get("at"), follow_up.deadline)
        if error:
            return error
        if at < follow_up.created_at:
            return jsonify({"error": "investigation not yet created at this time", "data_mode": "synthetic"}), 409
        investigation_row = store.get_investigation(investigation_id)
        scenario_name = investigation_row["scenario"] if investigation_row else "demo_v1"
        scn = _load_named_scenario(scenario_name) or scenario
        row_before = store.get_follow_up_row(investigation_id)
        latest_before = None
        if row_before and row_before.get("last_evaluated_at"):
            latest_before = datetime.fromisoformat(str(row_before["last_evaluated_at"]).replace("Z", "+00:00"))
        is_rewind = latest_before is not None and at < latest_before
        outcome = evaluate_outcome(follow_up, scn.records, at)
        if not is_rewind:
            store.record_outcome(investigation_id, outcome)
        outcome_payload = outcome.model_dump(mode="json")
        payload = {"data_mode": "synthetic", "investigation_id": investigation_id, "scenario": scn.manifest.id, "at": at.isoformat(), "timezone": scn.manifest.timezone, "status": outcome.status.value, "outcome": outcome_payload, "follow_up": _follow_up_payload(store, investigation_id, at=at, outcome=outcome), "supporting_ids": outcome.supporting_ids, "history": store.list_outcomes(investigation_id, at=at)}
        verification = None
        if any(r.source is SourceKind.room_sensor for r in scn.records):
            verification = verify_recovery(scn, follow_up, at)
            latest = verification.get("latest_reading_used")
            latest_payload = None
            if isinstance(latest, dict):
                latest_payload = {
                    "id": latest.get("id"),
                    "observed_at": latest["observed_at"].isoformat() if hasattr(latest.get("observed_at"), "isoformat") else latest.get("observed_at"),
                    "received_at": latest["received_at"].isoformat() if hasattr(latest.get("received_at"), "isoformat") else latest.get("received_at"),
                }
            payload["verification"] = {**verification, "evaluated_at": verification["evaluated_at"].isoformat(), "goal_verified_at": verification["goal_verified_at"].isoformat() if verification.get("goal_verified_at") else None, "arrival_met_at": verification["arrival_met_at"].isoformat() if verification.get("arrival_met_at") else None, "latest_reading_used": latest_payload}
            history_rows = payload["history"]
            verification_history = []
            for entry in history_rows:
                try:
                    entry_at = datetime.fromisoformat(str(entry["evaluated_at"]).replace("Z", "+00:00"))
                except ValueError:
                    continue
                entry_verification = verify_recovery(scn, follow_up, entry_at)
                verification_history.append({"evaluated_at": entry["evaluated_at"], "stage": entry_verification["stage"], "sample_count": entry.get("sample_count")})
            payload["verification_history"] = verification_history
        if scn.manifest.id == "demo_video_v1" and not is_rewind:
            stored_output = investigation_row["output"] if investigation_row else None
            pseudo = {"output": stored_output} if stored_output else None
            readiness_for_hvac = {"status": "cannot_tell", "reasons": list(verification["reasons"]) if verification else []}
            create_hvac_notification(store, scn, investigation_id, pseudo, readiness_for_hvac, at, verification=verification)
        payload["notifications"] = [_notification_api(r) for r in store.list_notifications(investigation_id, at=at)]
        return jsonify(payload)

    @app.get("/api/notifications")
    def list_notifications_endpoint():
        store = _get_store()
        investigation_id = request.args.get("investigation_id")
        raw_at = request.args.get("at")
        if raw_at:
            at, error = _parse_at(raw_at, None)
            if error:
                return error
            if investigation_id:
                follow_up = store.get_follow_up(investigation_id)
                created_at = follow_up.created_at if follow_up is not None else None
                if created_at is None:
                    inv_row = store.get_investigation(investigation_id)
                    if inv_row and inv_row.get("created_at"):
                        created_at = datetime.fromisoformat(str(inv_row["created_at"]).replace("Z", "+00:00"))
                if created_at is not None and at < created_at:
                    return jsonify({"error": "investigation not yet created at this time", "data_mode": "synthetic"}), 409
            rows = store.list_notifications(investigation_id, at=at)
            return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "at": at.isoformat(), "notifications": [_notification_api(r) for r in rows]})
        rows = store.list_notifications(investigation_id)
        return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "notifications": [_notification_api(r) for r in rows]})

    @app.post("/api/notifications/<notification_id>/ack")
    def ack_notification_endpoint(notification_id):
        store = _get_store()
        existing = store.get_notification(notification_id)
        if existing is None:
            return jsonify({"error": "notification not found", "data_mode": "synthetic"}), 404
        body = request.get_json(silent=True) or {}
        actor = body.get("actor") or body.get("by") or body.get("who") or request.args.get("actor") or "unknown"
        raw_at = body.get("at") or body.get("acknowledged_at") or body.get("when") or request.args.get("at")
        if raw_at:
            at, error = _parse_at(raw_at, None)
            if error:
                return error
        else:
            from datetime import timezone as _tz
            at = datetime.now(_tz.utc)
        ack = store.record_ack(notification_id, actor, at)
        updated = store.get_notification(notification_id)
        inv_row = store.get_investigation(updated["investigation_id"]) if updated else None
        ack_scenario = inv_row["scenario"] if inv_row else scenario.manifest.id
        ack_scn = _load_named_scenario(ack_scenario) or scenario
        return jsonify({"data_mode": "synthetic", "scenario": ack_scn.manifest.id, "at": at.isoformat(), "timezone": ack_scn.manifest.timezone, "message": "acknowledged, not resolved", "acknowledgement": "acknowledged, not resolved", "notification": _notification_api(updated), "ack": ack, "acks": updated["acks"] if updated else []})

    @app.after_request
    def _echo_context(response):
        if not request.path.startswith("/api/") or not response.is_json:
            return response
        payload = response.get_json(silent=True)
        if not isinstance(payload, dict):
            return response
        scn = _load_named_scenario(request.args.get("scenario")) or scenario
        if request.path.startswith("/api/follow-ups/") and payload.get("scenario"):
            scn = _load_named_scenario(payload.get("scenario")) or scn
        changed = False
        if "scenario" not in payload or payload.get("scenario") is None:
            payload["scenario"] = scn.manifest.id
            changed = True
        if "timezone" not in payload or payload.get("timezone") is None:
            payload["timezone"] = scn.manifest.timezone
            changed = True
        if "at" not in payload or payload.get("at") is None:
            raw_at = request.args.get("at")
            at_value = None
            if raw_at:
                try:
                    parsed = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
                    at_value = parsed.isoformat() if parsed.tzinfo else raw_at
                except ValueError:
                    at_value = raw_at
            else:
                at_value = (scn.manifest.start + timedelta(hours=3)).isoformat()
            payload["at"] = at_value
            changed = True
        if changed:
            import json as _json

            response.set_data(_json.dumps(payload))
        return response

    return app
