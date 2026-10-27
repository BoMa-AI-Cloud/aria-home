import json
from pathlib import Path

from aria_home.app import create_app


def test_evaluation_offline_returns_results_file():
    expected = json.loads(
        (Path(__file__).resolve().parent.parent / "eval" / "results-offline.json").read_text(encoding="utf-8")
    )
    resp = create_app().test_client().get("/api/evaluation/offline")
    assert resp.status_code == 200
    assert resp.get_json() == expected
    assert resp.get_json()["totals"]["combined"]["fully_correct"] == resp.get_json()["totals"]["combined"]["cases"]
