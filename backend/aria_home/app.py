"""Flask application factory for the ARIA Home backend."""
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, request

from aria_home.contracts import SourceKind
from aria_home.evidence import source_status
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

    return app
