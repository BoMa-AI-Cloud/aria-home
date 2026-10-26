"""Flask application factory for the ARIA Home backend."""
import os
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, request

from aria_home.contracts import SourceKind
from aria_home.evidence import source_status
from aria_home.metrics import NOISE_FLOOR_W, circuit_activity, target_gap, temperature_trend
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
        return jsonify(
            {
                "mode": selected.mode,
                "model_id": config.model_id,
                "enabled": config.enabled,
                "key_present": bool(config.api_key),
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

    return app
