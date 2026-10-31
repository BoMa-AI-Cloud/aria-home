"""A watcher citing a whole source (source:<kind>) is judged on that source's newest reading.

Source-status pack items carry `newest_observed_at`. The validator read only
`last_observed_at`/`latest_observed_at`, so every source citation was rejected as
"not fresh", even for an available source (found in the 2026-10-31 model-value run).
"""
from datetime import datetime
from pathlib import Path

from aria_home.investigator import build_evidence_pack
from aria_home.scenario import load_scenario
from aria_home.watcher import verify_observation

CARE = Path(__file__).resolve().parent.parent / "scenarios" / "care_home_v1"


def _reasons(source_id, at):
    at = datetime.fromisoformat(at)
    pack = build_evidence_pack(load_scenario(CARE), at)
    obs = {"evidence_ids": [source_id], "values": {}}
    return verify_observation(obs, pack, at)


def _stale(reasons, source_id):
    text = " ".join(reasons if isinstance(reasons, list) else reasons.get("reasons", []))
    return f"evidence {source_id} is not fresh" in text


def test_available_room_sensor_source_is_fresh():
    assert not _stale(_reasons("source:room_sensor", "2026-01-17T02:31:00-05:00"), "source:room_sensor")


def test_silent_thermostat_source_is_still_stale():
    assert _stale(_reasons("source:thermostat", "2026-01-17T02:31:00-05:00"), "source:thermostat")
