import json
from pathlib import Path

from aria_home.app import create_app


def test_evaluation_offline_returns_results_file():
    expected = json.loads(
        (Path(__file__).resolve().parent.parent / "eval" / "results-offline.json").read_text(encoding="utf-8")
    )
    resp = create_app().test_client().get("/api/evaluation/offline")
    assert resp.status_code == 200
    assert resp.get_json() == {
        **expected,
        "scenario": "care_home_v1",
        "at": "2026-01-16T19:00:00-05:00",
        "timezone": "America/New_York",
    }
    assert resp.get_json()["totals"]["combined"]["fully_correct"] == resp.get_json()["totals"]["combined"]["cases"]
