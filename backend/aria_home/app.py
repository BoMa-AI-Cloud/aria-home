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
from aria_home.scenario import load_scenario, visible_records

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
        statuses = [
            source_status(source, visible, at, mode=scenario.manifest.mode)
            for source in SourceKind
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
        zones = sorted({r.subject for r in scenario.records if r.quantity == "indoor_temp"})
        zone = zones[0] if zones else "demo-cabin/main"
        trend = temperature_trend(scenario.records, zone, start, at, at)
        gap = None
        if scenario.confirmation is not None:
            gap = target_gap(trend, scenario.confirmation.target_temp, scenario.confirmation.target_unit)
        circuit_ids = sorted(
            {
                (r.binding.circuit_id if r.binding else None) or r.subject
                for r in scenario.records
                if r.quantity == "circuit_power"
            }
        )
        return jsonify(
            {
                "data_mode": scenario.manifest.mode.value,
                "computed_by": "deterministic code",
                "at": at.isoformat(),
                "zone": zone,
                "window": {"start": start.isoformat(), "end": at.isoformat()},
                "indoor_trend": _jsonable(trend),
                "target_gap": _jsonable(gap),
                "circuits": {cid: _jsonable(circuit_activity(scenario.records, cid, start, at, at)) for cid in circuit_ids},
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

    def _follow_up_payload(store, investigation_id):
        follow_up = store.get_follow_up(investigation_id)
        row = store.get_follow_up_row(investigation_id)
        if follow_up is None:
            return None
        payload = follow_up.model_dump(mode="json")
        payload.update({"target": row["target"], "last_status": row["last_status"], "status": row["last_status"], "last_evaluated_at": row["last_evaluated_at"], "supporting_ids": row["supporting_ids"]})
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
        try:
            follow_up = follow_up_for(scn, investigation_id, at)
        except ValueError as exc:
            return jsonify({"error": str(exc), "data_mode": "synthetic"}), 400
        outcome = evaluate_outcome(follow_up, scn.records, at)
        store.save_follow_up(follow_up, outcome=outcome)
        investigation_payload = result.model_dump(mode="json")
        investigation_payload.update({"id": investigation_id, "investigation_id": investigation_id, "scenario": scn.manifest.id, "evaluated_at": at.isoformat()})
        return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "status": result.status, "investigation": investigation_payload, "follow_up": _follow_up_payload(store, investigation_id), "outcome": outcome.model_dump(mode="json")})

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
        return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "scenario": scn.manifest.id, "status": outcome.status.value, "outcome": outcome_payload, "follow_up": _follow_up_payload(store, investigation_id), "supporting_ids": outcome.supporting_ids, "history": store.list_outcomes(investigation_id)})

    return app
