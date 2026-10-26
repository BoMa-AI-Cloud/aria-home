"""Flask application factory for the ARIA Home backend."""
from flask import Flask, jsonify


def create_app():
    app = Flask(__name__)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "aria-home-backend", "data_mode": "synthetic"})

    return app
