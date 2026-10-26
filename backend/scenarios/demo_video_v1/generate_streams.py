"""Generate the synthetic sensor streams for demo_video_v1.

All data generated here is synthetic. Rerun with:
    python backend/scenarios/demo_video_v1/generate_streams.py
It deterministically (stdlib only, no randomness) rewrites thermostat.json,
room_sensor.json and electrical.json in its own folder.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

TZ = timezone(timedelta(hours=-5))
DAY = datetime(2026, 1, 16, tzinfo=TZ)
HERE = Path(__file__).resolve().parent
PROVENANCE = {"fixture_id": "demo_video_v1", "version": "1"}


def at(hour, minute=0):
    return DAY.replace(hour=hour, minute=minute)


def stamps(start, end):
    out = []
    t = start
    while t <= end:
        out.append(t)
        t += timedelta(minutes=5)
    return out


def fmt(t):
    return t.isoformat()


def received(t):
    return t + timedelta(seconds=20)


def room_temp(t):
    if t <= at(15, 30):
        frac = (t - at(6)) / (at(15, 30) - at(6))
        return round(55.0 - 3.0 * frac, 1)
    if t <= at(18, 35):
        return 52.0
    if t <= at(18, 50):
        frac = (t - at(18, 35)) / (at(18, 50) - at(18, 35))
        return round(52.0 + 2.5 * frac, 1)
    if t <= at(19, 50):
        frac = (t - at(18, 50)) / (at(19, 50) - at(18, 50))
        return round(54.5 + 13.5 * frac, 1)
    steps = int((t - at(19, 50)) / timedelta(minutes=5))
    return [68.0, 68.2, 68.4, 68.6, 68.4, 68.2][steps % 6]


def record(rid, source, kind, quantity, value, unit, t, cadence, **extra):
    row = {
        "id": rid,
        "source": source,
        "kind": kind,
        "subject": "demo-cabin/main",
        "quantity": quantity,
        "value": value,
        "unit": unit,
        "observed_at": fmt(t),
        "received_at": fmt(received(t)),
        "expected_cadence_s": cadence,
        "mode": "synthetic",
        "provenance": PROVENANCE,
    }
    row.update(extra)
    return row


def main():
    room_times = stamps(at(6), at(21, 30))
    room = [
        record(f"room-temp-{t:%H%M}", "room_sensor", "measurement", "indoor_temp", room_temp(t), "F", t, 300)
        for t in room_times
    ]

    thermostat = []
    thermo_times = stamps(at(6), at(15, 30)) + stamps(at(18, 20), at(21, 30))
    for t in thermo_times:
        thermostat.append(
            record(f"tstat-video-temp-{t:%H%M}", "thermostat", "measurement", "indoor_temp", round(room_temp(t) + 0.2, 1), "F", t, 300)
        )
        state = "heating" if t >= at(14, 5) else "idle"
        thermostat.append(
            record(f"tstat-video-state-{t:%H%M}", "thermostat", "device_report", "hvac_reported_state", state, None, t, 300)
        )

    electrical = []
    blower_cycle = [450, 500, 550, 480, 520, 580]
    furnace_cycle = [900, 920, 880, 910, 895, 915]
    kitchen_cycle = [140, 260, 450, 180, 320, 90]
    living_cycle = [85, 120, 160, 95, 140, 110]
    elec_times = []
    t = at(6)
    while t <= at(21, 30):
        elec_times.append(t)
        t += timedelta(minutes=30)
    for i, t in enumerate(elec_times):
        if t < at(15, 30):
            blower = 5
        elif t < at(18, 30):
            blower = blower_cycle[i % len(blower_cycle)]
        else:
            blower = furnace_cycle[i % len(furnace_cycle)]
        circuits = [
            ("circuit-blower", blower, {"equipment": "blower", "status": "candidate", "confirmed_by": None}),
            ("circuit-kitchen", kitchen_cycle[i % len(kitchen_cycle)], {"equipment": None, "status": "unknown", "confirmed_by": None}),
            ("circuit-living", living_cycle[i % len(living_cycle)], {"equipment": None, "status": "unknown", "confirmed_by": None}),
        ]
        for circuit, watts, binding in circuits:
            name = circuit.removeprefix("circuit-")
            electrical.append(
                record(
                    f"elec-video-{name}-{t:%H%M}",
                    "electrical",
                    "measurement",
                    "circuit_power",
                    watts,
                    "W",
                    t,
                    1800,
                    subject=circuit,
                    meter_id="demo-cabin-meter-1",
                    binding={"circuit_id": circuit, **binding},
                )
            )

    for filename, rows in [
        ("thermostat.json", thermostat),
        ("room_sensor.json", room),
        ("electrical.json", electrical),
    ]:
        (HERE / filename).write_text(json.dumps({"records": rows}, indent=2) + "\n", encoding="utf-8")
        print(f"{filename}: {len(rows)}")


if __name__ == "__main__":
    main()
