"""Generate 12 deterministic synthetic eval variants from care_home_v1 (offline).

Each variant is a full scenario directory under backend/scenarios/eval_variants/
with unseen ids, plus a variant.json carrying the code-computed expected
readiness/verification labels and a human-written ground-truth note. Nothing
here is imported by prompts, fixtures or recordings; it is input to the
model-value evaluation only.

Regenerate byte-identically with the fixed seed:

    python backend/scripts/make_eval_variants.py
    python backend/scripts/make_eval_variants.py --out <dir>
"""
import argparse
import copy
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

SEED = 20261030
SRC_DIR = BACKEND_DIR / "scenarios" / "care_home_v1"
DEFAULT_OUT = BACKEND_DIR / "scenarios" / "eval_variants"
TZ = "-05:00"
DAY1 = "2026-01-16"
DAY2 = "2026-01-17"
STEP_S = 300
START = datetime.fromisoformat(f"{DAY1}T16:00:00{TZ}")
END = datetime.fromisoformat(f"{DAY2}T07:30:00{TZ}")
TARGET_TEMP = 68


def _iso(minute):
    return (START + timedelta(minutes=minute)).isoformat()


def _recv(minute):
    return (START + timedelta(minutes=minute, seconds=20)).isoformat()


SPECS = [
    dict(
        id="ev-outage-2310", code="ev01",
        description="Furnace stops 23:10, no repair before evaluation; room cools, thermostat dark.",
        room=[(0, 66.0), (430, 66.0), (645, 62.5), (1050, 57.5)],
        tstat="room", tstat_gap=(430, None),
        followup_at=f"{DAY2}T00:30:00{TZ}", eval_at=f"{DAY2}T02:45:00{TZ}",
        events="base",
        ground_truth={
            "problem": "Furnace stopped around 23:10; living area cooling through the night.",
            "next_action": "Dispatch HVAC technician now; keep the warm-by plan under watch.",
        },
    ),
    dict(
        id="ev-outage-0130", code="ev02",
        description="Furnace stops 01:30 (care-night timing), deeper cooling; thermostat dark.",
        room=[(0, 66.0), (570, 66.0), (645, 64.2), (1050, 55.0)],
        tstat="room", tstat_gap=(570, None),
        followup_at=f"{DAY2}T00:30:00{TZ}", eval_at=f"{DAY2}T02:45:00{TZ}",
        events="base",
        ground_truth={
            "problem": "Furnace stopped around 01:30; room falling fast with no heat.",
            "next_action": "Dispatch HVAC technician now; notify the caregiver.",
        },
    ),
    dict(
        id="ev-outage-0340", code="ev03",
        description="Furnace stops 03:40, steep drop; evaluated 04:51 with little history after the stop.",
        room=[(0, 66.0), (700, 66.0), (771, 63.6), (1050, 56.0)],
        tstat="room", tstat_gap=(700, None),
        followup_at=f"{DAY2}T02:45:00{TZ}", eval_at=f"{DAY2}T04:51:00{TZ}",
        events="base",
        ground_truth={
            "problem": "Furnace stopped around 03:40; steep late-night drop.",
            "next_action": "Dispatch HVAC technician now; warm-by time is at risk.",
        },
    ),
    dict(
        id="ev-recovery-fails", code="ev04",
        description="Repair warms the house to the goal, holds briefly, then temperature dips again.",
        room=[(0, 66.0), (570, 66.0), (600, 65.2), (688, 68.2), (850, 68.5), (860, 66.6), (1050, 66.6)],
        tstat="room", tstat_gap=(570, 620), tstat_heat=(600, 850),
        followup_at=f"{DAY2}T02:45:00{TZ}", eval_at=f"{DAY2}T06:45:00{TZ}",
        events="visit",
        ground_truth={
            "problem": "Repair warmed the house but the goal did not hold; readings fell back below 68 F.",
            "next_action": "Re-dispatch the technician; the earlier fix did not hold.",
        },
    ),
    dict(
        id="ev-slow-cool-ontrack", code="ev05",
        description="Slow overnight cooling that never leaves the goal; no outage at all.",
        room=[(0, 69.6), (645, 68.4), (1050, 67.9)],
        tstat="room", tstat_gap=None,
        followup_at=f"{DAY2}T00:30:00{TZ}", eval_at=f"{DAY2}T02:45:00{TZ}",
        events="base",
        ground_truth={
            "problem": "No real problem; slow cooling stays above the 68 F goal.",
            "next_action": "No action; routine next check only.",
        },
    ),
    dict(
        id="ev-thermostat-gap-steady", code="ev06",
        description="Thermostat radio dies 01:30 but the room sensor holds steady at goal; no heating fault.",
        room=[(0, 68.5), (1050, 68.5)],
        tstat="room", tstat_gap=(570, None),
        followup_at=f"{DAY2}T00:30:00{TZ}", eval_at=f"{DAY2}T02:45:00{TZ}",
        events="base",
        ground_truth={
            "problem": "No heating problem; the thermostat link alone is dead while the room holds at goal.",
            "next_action": "Check the thermostat link/battery; do not dispatch HVAC.",
        },
    ),
    dict(
        id="ev-stale-room", code="ev07",
        description="Room sensor silent since 20:00; thermostat keeps reporting cooler values.",
        room=[(0, 66.5), (240, 66.5)], room_end=240,
        tstat=[(0, 66.5), (645, 62.6), (1050, 60.0)], tstat_gap=None,
        followup_at=f"{DAY2}T00:30:00{TZ}", eval_at=f"{DAY2}T02:45:00{TZ}",
        events="base",
        ground_truth={
            "problem": "Room sensor stale since 20:00; the true room temperature cannot be told.",
            "next_action": "Restore an independent room reading before deciding on dispatch.",
        },
    ),
    dict(
        id="ev-wrong-zone", code="ev08",
        description="Thermostat reports a different zone (upstairs) while the main room cools.",
        room=[(0, 66.0), (570, 66.0), (645, 64.2), (1050, 55.0)],
        tstat=[(0, 65.0), (1050, 65.0)], tstat_gap=None, tstat_subject="demo-house/upstairs",
        followup_at=f"{DAY2}T00:30:00{TZ}", eval_at=f"{DAY2}T02:45:00{TZ}",
        events="base",
        ground_truth={
            "problem": "Furnace outage cools the main room; the thermostat reading is from the wrong zone and must be ignored.",
            "next_action": "Dispatch HVAC on the room-sensor evidence; fix the thermostat zone binding.",
        },
    ),
    dict(
        id="ev-report-no-warm", code="ev09",
        description="Technician visit and completion report filed, but room readings show no warming after.",
        room=[(0, 66.0), (430, 66.0), (645, 62.6), (770, 61.8), (1050, 61.9)],
        tstat="room", tstat_gap=(430, 740),
        followup_at=f"{DAY2}T00:30:00{TZ}", eval_at=f"{DAY2}T06:45:00{TZ}",
        events="report",
        ground_truth={
            "problem": "Completion report claims a fix, but independent readings show no warming; the report proves nothing.",
            "next_action": "Re-dispatch; do not close on the report alone.",
        },
    ),
    dict(
        id="ev-normal-night", code="ev10",
        description="Control: steady warm night, all telemetry fresh, nothing wrong.",
        room=[(0, 68.6), (1050, 68.6)],
        tstat="room", tstat_gap=None,
        followup_at=f"{DAY2}T00:30:00{TZ}", eval_at=f"{DAY2}T02:45:00{TZ}",
        events="base",
        ground_truth={
            "problem": "Normal night; house at goal with fresh telemetry.",
            "next_action": "No action; routine next check only.",
        },
    ),
    dict(
        id="ev-conflict-sensors", code="ev11",
        description="Two room sensors disagree sharply at the same times; the truth cannot be told.",
        room=[(0, 66.0), (570, 66.0), (645, 64.0), (1050, 56.0)],
        room_b=[(0, 68.6), (1050, 68.4)],
        tstat="room", tstat_gap=None,
        followup_at=f"{DAY2}T00:30:00{TZ}", eval_at=f"{DAY2}T02:45:00{TZ}",
        events="base",
        ground_truth={
            "problem": "Room sensors contradict each other; no trustworthy room temperature.",
            "next_action": "Inspect the sensors on site; do not decide dispatch from these readings.",
        },
    ),
    dict(
        id="ev-arrival-met", code="ev12",
        description="Repair holds the goal through the 07:00 warm-by time; evaluated after arrival.",
        room=[(0, 66.0), (430, 66.0), (600, 60.0), (696, 68.2), (1050, 68.6)],
        tstat="room", tstat_gap=(430, 620), tstat_heat=(600, 1050),
        followup_at=f"{DAY2}T02:45:00{TZ}", eval_at=f"{DAY2}T07:30:00{TZ}",
        events="report",
        ground_truth={
            "problem": "Earlier outage recovered; the goal held through the warm-by time.",
            "next_action": "No action; confirm routine monitoring only.",
        },
    ),
]

BASE_EVENTS = [
    ("evt-care-confirmation-request", "confirmation_request", f"{DAY1}T19:15:00{TZ}", f"{DAY1}T19:15:00{TZ}"),
    ("evt-care-caregiver-alert", "caregiver_alert", f"{DAY2}T02:35:00{TZ}", f"{DAY2}T02:37:00{TZ}"),
    ("evt-care-caregiver-hvac-authorized", "caregiver_hvac_authorized", f"{DAY2}T02:45:00{TZ}", f"{DAY2}T02:45:00{TZ}"),
]
VISIT_EVENTS = [
    ("evt-care-hvac-request", "hvac_request", f"{DAY2}T02:50:00{TZ}", f"{DAY2}T02:52:00{TZ}"),
    ("evt-care-service-visit", "service_visit", f"{DAY2}T03:30:00{TZ}", f"{DAY2}T04:15:00{TZ}"),
]
REPORT_EVENTS = [
    ("evt-care-hvac-completion-report", "hvac_completion_report", f"{DAY2}T06:40:00{TZ}", f"{DAY2}T06:45:00{TZ}"),
]


def _interp(points, minute):
    if minute <= points[0][0]:
        return points[0][1]
    for (m0, v0), (m1, v1) in zip(points, points[1:]):
        if minute <= m1:
            frac = (minute - m0) / (m1 - m0) if m1 > m0 else 0.0
            return v0 + frac * (v1 - v0)
    return points[-1][1]


def _in_gap(minute, gap):
    return gap is not None and minute >= gap[0] and (gap[1] is None or minute < gap[1])


def _dump(path, payload):
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _rewrite_copied(records, code, variant_id):
    out = []
    for record in records:
        item = copy.deepcopy(record)
        item["id"] = f"{code}-{item['id']}"
        item["mode"] = "synthetic"
        provenance = item.get("provenance")
        if isinstance(provenance, dict):
            provenance["fixture_id"] = variant_id
            provenance["version"] = "1"
        out.append(item)
    return out


def _build_room(spec, rng):
    points = spec["room"]
    end = spec.get("room_end")
    records = []
    seq = 0
    while True:
        minute = seq * (STEP_S // 60)
        if end is not None and minute > end:
            break
        if START + timedelta(minutes=minute) > END:
            break
        value = round(_interp(points, minute) + rng.uniform(-0.15, 0.15), 1)
        records.append({
            "id": f"{spec['code']}-room-{seq:04d}",
            "source": "room_sensor",
            "kind": "measurement",
            "subject": "demo-house/main",
            "quantity": "indoor_temp",
            "value": value,
            "unit": "F",
            "observed_at": _iso(minute),
            "received_at": _recv(minute),
            "expected_cadence_s": STEP_S,
            "mode": "synthetic",
            "provenance": {"fixture_id": spec["id"], "version": "1"},
        })
        seq += 1
    if "room_b" in spec:
        for seq_b, record in enumerate(list(records)):
            minute = seq_b * (STEP_S // 60)
            value = round(_interp(spec["room_b"], minute) + rng.uniform(-0.15, 0.15), 1)
            twin = dict(record)
            twin["id"] = f"{spec['code']}-roomb-{seq_b:04d}"
            twin["value"] = value
            records.append(twin)
        records.sort(key=lambda r: (r["observed_at"], r["id"]))
    return records


def _build_thermostat(spec, rng):
    configured = spec.get("tstat")
    points = spec["room"] if configured == "room" else configured
    gap = spec.get("tstat_gap")
    heat = spec.get("tstat_heat")
    subject = spec.get("tstat_subject", "demo-house/main")
    records = []
    seq = 0
    while True:
        minute = seq * (STEP_S // 60)
        if START + timedelta(minutes=minute) > END:
            break
        if not _in_gap(minute, gap):
            value = round(_interp(points, minute) + rng.uniform(-0.15, 0.15), 1)
            state = "heating" if heat is not None and heat[0] <= minute < heat[1] else "idle"
            records.append({
                "id": f"{spec['code']}-tstat-temp-{seq:04d}",
                "source": "thermostat",
                "kind": "measurement",
                "subject": subject,
                "quantity": "indoor_temp",
                "value": value,
                "unit": "F",
                "observed_at": _iso(minute),
                "received_at": _recv(minute),
                "expected_cadence_s": STEP_S,
                "mode": "synthetic",
                "provenance": {"fixture_id": spec["id"], "version": "1"},
            })
            records.append({
                "id": f"{spec['code']}-tstat-state-{seq:04d}",
                "source": "thermostat",
                "kind": "device_report",
                "subject": subject,
                "quantity": "hvac_reported_state",
                "value": state,
                "unit": None,
                "observed_at": _iso(minute),
                "received_at": _recv(minute),
                "expected_cadence_s": STEP_S,
                "mode": "synthetic",
                "provenance": {"fixture_id": spec["id"], "version": "1"},
            })
        seq += 1
    return records


def _build_events(spec):
    kinds = {"events": []}
    selected = list(BASE_EVENTS)
    if spec["events"] in ("visit", "report"):
        selected += VISIT_EVENTS
    if spec["events"] == "report":
        selected += REPORT_EVENTS
    for raw_id, kind, event_time, available_at in selected:
        kinds["events"].append({
            "id": f"{spec['code']}-{raw_id}",
            "kind": kind,
            "event_time": event_time,
            "available_at": available_at,
            "simulated": True,
            "payload": {"label": f"synthetic {kind} for {spec['id']}"},
        })
    return kinds


def _load_src(name):
    return json.loads((SRC_DIR / name).read_text(encoding="utf-8"))


def build_variant(spec, out_dir):
    rng = random.Random(SEED + SPECS.index(spec))
    target = out_dir / spec["id"]
    target.mkdir(parents=True, exist_ok=True)
    manifest = _load_src("manifest.json")
    manifest["id"] = spec["id"]
    manifest["version"] = "1"
    manifest["description"] = f"Synthetic model-value eval variant of care_home_v1 (seed {SEED}): {spec['description']}"
    _dump(target / "manifest.json", manifest)
    calendar = _load_src("calendar.json")
    calendar["records"] = _rewrite_copied(calendar.get("records", []), spec["code"], spec["id"])
    _dump(target / "calendar.json", calendar)
    for name in ("electrical.json", "weather.json"):
        payload = _load_src(name)
        payload["records"] = _rewrite_copied(payload.get("records", []), spec["code"], spec["id"])
        _dump(target / name, payload)
    _dump(target / "room_sensor.json", {"records": _build_room(spec, rng)})
    _dump(target / "thermostat.json", {"records": _build_thermostat(spec, rng)})
    _dump(target / "events.json", _build_events(spec))
    return target


def label_variant(variant_dir):
    from aria_home.investigator import build_evidence_pack
    from aria_home.outcomes import follow_up_for
    from aria_home.scenario import load_scenario
    from aria_home.verification import verify_recovery

    scenario = load_scenario(variant_dir)
    spec = next(s for s in SPECS if s["id"] == variant_dir.name)
    at = datetime.fromisoformat(spec["eval_at"])
    created = datetime.fromisoformat(spec["followup_at"])
    pack = build_evidence_pack(scenario, at)
    followup = follow_up_for(scenario, f"inv-{spec['id']}", created)
    verification = verify_recovery(scenario, followup, at)
    return {
        "id": spec["id"],
        "source_scenario": "care_home_v1",
        "seed": SEED,
        "description": spec["description"],
        "eval_at": spec["eval_at"],
        "followup_created_at": spec["followup_at"],
        "followup_target": {"target_temp": TARGET_TEMP, "target_unit": "F"},
        "expected_readiness": pack["computed_readiness"],
        "expected_verification": verification["stage"],
        "ground_truth": spec["ground_truth"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(prog="make_eval_variants", description="Generate deterministic eval variants")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    out_dir = Path(args.out) if args.out else DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    for spec in SPECS:
        variant_dir = build_variant(spec, out_dir)
        _dump(variant_dir / "variant.json", label_variant(variant_dir))
        print(f"wrote {spec['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
