"""Flask application factory for the ARIA Home backend."""
import os
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, request

from aria_home.contracts import SourceKind
from aria_home.evidence import source_status
from aria_home.metrics import NOISE_FLOOR_W, circuit_activity, target_gap, temperature_trend
from aria_home.investigator import investigate
from aria_home.outcomes import evaluate_outcome, follow_up_for
from aria_home.store import Store, investigation_id_for
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
        return jsonify({"status": "ok", "service": "aria-home-backend", "data_mode": "synthetic"})

    @app.get("/api/sources")
    def sources():
        raw_at = request.args.get("at")
        if raw_at:
            try:
                at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "at must be an ISO 8601 datetime"}), 400
            if at.tzinfo is None or at.utcoffset() is None:
                return jsonify({"error": "at must be timezone-aware"}), 400
        else:
            at = scenario.manifest.start + timedelta(hours=3)

        visible = visible_records(scenario.records, at)
        has_room_sensor = any(r.source is SourceKind.room_sensor for r in scenario.records)
        statuses = [
            source_status(source, visible, at, mode=scenario.manifest.mode)
            for source in SourceKind
            if source is not SourceKind.room_sensor or has_room_sensor
        ]
        return jsonify(
            {
                "data_mode": scenario.manifest.mode.value,
                "at": at.isoformat(),
                "sources": [s.model_dump(mode="json") for s in statuses],
            }
        )

    @app.get("/api/provider")
    def provider():
        try:
            config = ProviderConfig.from_env(os.environ)
            selected = get_provider(config)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        missing = config.missing_settings() if config.enabled else None
        return jsonify(
            {
                "mode": selected.mode,
                "model_id": config.model_id,
                "enabled": config.enabled,
                "key_present": bool(config.api_key),
                "configured": config.configured,
                "config_error": missing or None,
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

        raw_at = request.args.get("at")
        if raw_at:
            try:
                at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "at must be an ISO 8601 datetime"}), 400
            if at.tzinfo is None or at.utcoffset() is None:
                return jsonify({"error": "at must be timezone-aware"}), 400
        else:
            at = scenario.manifest.start + timedelta(hours=3)

        start = at - timedelta(hours=3)
        ctx = context_as_of(scenario, at)
        visible = visible_records(scenario.records, at)
        zones = sorted({r.subject for r in visible if r.quantity == "indoor_temp"})
        zone = zones[0] if zones else "demo-cabin/main"
        trend = temperature_trend(visible, zone, start, at, at)
        gap = None
        if ctx.confirmation is not None:
            gap = target_gap(trend, ctx.confirmation.target_temp, ctx.confirmation.target_unit)
        circuit_ids = sorted(
            {
                (r.binding.circuit_id if r.binding else None) or r.subject
                for r in visible
                if r.quantity == "circuit_power"
            }
        )
        circuits = {cid: _jsonable(circuit_activity(visible, cid, start, at, at)) for cid in circuit_ids}
        statuses = [
            source_status(source, visible, at, mode=scenario.manifest.mode)
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
                "data_mode": scenario.manifest.mode.value,
                "computed_by": "deterministic code",
                "at": at.isoformat(),
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
        raw_at = request.args.get("at")
        if raw_at:
            try:
                at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "at must be an ISO 8601 datetime"}), 400
            if at.tzinfo is None or at.utcoffset() is None:
                return jsonify({"error": "at must be timezone-aware"}), 400
        else:
            at = scenario.manifest.start + timedelta(hours=3)
        start = at - timedelta(hours=3)
        visible = visible_records(scenario.records, at)
        result = power_context(visible, start, at, NOISE_FLOOR_W)
        payload = result.model_dump(mode="json")
        payload.update(
            {
                "data_mode": scenario.manifest.mode.value,
                "computed_by": "deterministic code",
                "at": at.isoformat(),
                "window": {"start": start.isoformat(), "end": at.isoformat()},
            }
        )
        return jsonify(payload)

    @app.get("/api/investigation")
    def investigation():
        raw_at = request.args.get("at")
        if raw_at:
            try:
                at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "at must be an ISO 8601 datetime"}), 400
            if at.tzinfo is None or at.utcoffset() is None:
                return jsonify({"error": "at must be timezone-aware"}), 400
        else:
            at = scenario.manifest.start + timedelta(hours=3)
        try:
            provider = get_provider()
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        result = investigate(scenario, at, provider)
        payload = result.model_dump(mode="json")
        payload["data_mode"] = "synthetic"
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

    def _follow_up_payload(store, investigation_id):
        follow_up = store.get_follow_up(investigation_id)
        row = store.get_follow_up_row(investigation_id)
        if follow_up is None:
            return None
        payload = follow_up.model_dump(mode="json")
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
        result = investigate(scn, at, provider)
        investigation_id = investigation_id_for(scn.manifest.id, at)
        store = _get_store()
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
            return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "status": "deadline_passed", "investigation_status": result.status, "readiness": readiness, "computed_readiness": computed_readiness, "investigation": investigation_payload, "follow_up": None, "follow_up_schedule": schedule_payload, "schedule": schedule_payload, "schedule_status": "deadline_passed", "flag": "deadline_passed", "deadline_passed": True, "next_check_at": None, "outcome": None, "notifications": notif_rows})
        try:
            follow_up = follow_up_for(scn, investigation_id, at, cadence_s=cadence_s)
        except ValueError as exc:
            if "deadline_passed" in str(exc):
                return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "status": "deadline_passed", "investigation_status": result.status, "readiness": readiness, "computed_readiness": computed_readiness, "investigation": investigation_payload, "follow_up": None, "follow_up_schedule": schedule_payload, "schedule": schedule_payload, "schedule_status": "deadline_passed", "flag": "deadline_passed", "deadline_passed": True, "next_check_at": None, "outcome": None, "notifications": notif_rows})
            if any(token in str(exc) for token in ("trip_cancelled", "trip_unconfirmed", "trip_mismatched", "confirmation_outdated", "no homeowner confirmation", "no trip visible")):
                primary = next((name for name in ("trip_cancelled", "confirmation_outdated", "trip_mismatched", "trip_unconfirmed") if ctx.flags.get(name)), "trip_unconfirmed")
                not_scheduled = {**schedule_payload, "status": "not_scheduled", "schedule_status": "not_scheduled", "next_check_at": None, "when": None}
                return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "status": "cannot_tell", "investigation_status": result.status, "readiness": readiness, "computed_readiness": computed_readiness, "investigation": investigation_payload, "follow_up": None, "follow_up_schedule": not_scheduled, "schedule": not_scheduled, "schedule_status": "not_scheduled", "flag": primary, "flags": dict(ctx.flags), "readiness_flags": dict(ctx.flags), "context_flags": dict(ctx.flags), "deadline_passed": False, "next_check_at": None, "outcome": None, "error": str(exc), "notifications": notif_rows})
            return jsonify({"error": str(exc), "data_mode": "synthetic"}), 400
        if follow_up.next_check_at is None or follow_up.next_check_at.tzinfo is None or follow_up.next_check_at <= follow_up.created_at:
            return jsonify({"error": "invalid follow-up schedule", "data_mode": "synthetic"}), 400
        try:
            outcome = evaluate_outcome(follow_up, scn.records, at)
            store.save_follow_up(follow_up, outcome=outcome)
        except ValueError as exc:
            return jsonify({"error": str(exc), "data_mode": "synthetic"}), 400
        return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "status": result.status, "readiness": readiness, "computed_readiness": computed_readiness, "investigation": investigation_payload, "follow_up": _follow_up_payload(store, investigation_id), "follow_up_schedule": schedule_payload, "schedule": schedule_payload, "schedule_status": schedule["status"], "deadline_passed": False, "next_check_at": schedule_payload["next_check_at"], "outcome": outcome.model_dump(mode="json"), "notifications": notif_rows})

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
        investigation_row = store.get_investigation(investigation_id)
        scenario_name = investigation_row["scenario"] if investigation_row else "demo_v1"
        scn = _load_named_scenario(scenario_name) or scenario
        outcome = evaluate_outcome(follow_up, scn.records, at)
        store.record_outcome(investigation_id, outcome)
        outcome_payload = outcome.model_dump(mode="json")
        payload = {"data_mode": "synthetic", "investigation_id": investigation_id, "scenario": scn.manifest.id, "status": outcome.status.value, "outcome": outcome_payload, "follow_up": _follow_up_payload(store, investigation_id), "supporting_ids": outcome.supporting_ids, "history": store.list_outcomes(investigation_id)}
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
            payload["verification"] = {**verification, "evaluated_at": verification["evaluated_at"].isoformat(), "latest_reading_used": latest_payload}
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
        if scn.manifest.id == "demo_video_v1":
            stored_output = investigation_row["output"] if investigation_row else None
            pseudo = {"output": stored_output} if stored_output else None
            readiness_for_hvac = {"status": "cannot_tell", "reasons": list(verification["reasons"]) if verification else []}
            create_hvac_notification(store, scn, investigation_id, pseudo, readiness_for_hvac, at, verification=verification)
        payload["notifications"] = [_notification_api(r) for r in store.list_notifications(investigation_id)]
        return jsonify(payload)

    @app.get("/api/notifications")
    def list_notifications_endpoint():
        store = _get_store()
        investigation_id = request.args.get("investigation_id")
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
        return jsonify({"data_mode": "synthetic", "message": "acknowledged, not resolved", "acknowledgement": "acknowledged, not resolved", "notification": _notification_api(updated), "ack": ack, "acks": updated["acks"] if updated else []})

    return app
