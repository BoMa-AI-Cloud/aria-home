import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from aria_home.app import create_app
from aria_home.investigator import build_evidence_pack
from aria_home.notifications import build_payload
from aria_home.outcomes import follow_up_for
from aria_home.readiness import compute_readiness
from aria_home.scenario import context_as_of, load_scenario, visual_as_of
from aria_home.verification import verify_recovery
from aria_home.visual import (
    FIXTURES_DIR,
    IMAGE_GENERATOR,
    SAM_MODEL_ID,
    ReplayVisualProvider,
    SamLiveProvider,
    VisualConfig,
    extract_sam_text,
    largest_box_fraction,
    no_detection_line,
    observation_line,
    parse_sam_text,
)
from aria_home.whatsapp import build_hvac_whatsapp_text

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
AT_1800 = datetime.fromisoformat("2026-01-16T18:00:00-05:00")
WATER_LINE = "visual observation: water detected (synthetic image)"


def _recording(image_id):
    return (FIXTURES_DIR / f"{image_id}.sam.txt").read_text(encoding="utf-8")


def _counts():
    return {
        image_id: len(parse_sam_text(extract_sam_text(_recording(image_id))))
        for image_id in ("v1-water-floor", "v2-frost-pipe", "v3-dry-floor", "v4-frost-window")
    }


def test_parser_counts_recorded_responses():
    assert _counts() == {"v1-water-floor": 1, "v2-frost-pipe": 0, "v3-dry-floor": 0, "v4-frost-window": 4}


def test_parser_water_box_fraction():
    boxes = parse_sam_text(extract_sam_text(_recording("v1-water-floor")))
    assert len(boxes) == 1
    box = boxes[0]
    assert (box.x1, box.y1, box.x2, box.y2) == (417, 710, 1419, 1049)
    assert (box.image_width, box.image_height) == (2016, 1152)
    assert largest_box_fraction(boxes) == pytest.approx((1002 * 339) / (2016 * 1152))
    assert largest_box_fraction([]) == 0.0


def test_parser_frost_window_boxes():
    boxes = parse_sam_text(extract_sam_text(_recording("v4-frost-window")))
    assert len(boxes) == 4
    assert [box.index for box in boxes] == [0, 1, 2, 3]
    assert largest_box_fraction(boxes) > 0.0


def test_replay_observation_record_fields():
    observation = ReplayVisualProvider().observe(
        "v1-water-floor",
        "water puddle",
        observed_at="2026-01-16T17:56:00-05:00",
        received_at="2026-01-16T17:56:30-05:00",
        file="v1-water-floor.webp",
    )
    record = observation.as_dict()
    assert record["object_count"] == 1
    assert record["image_synthetic"] is True
    assert record["generator"] == IMAGE_GENERATOR == "muse-image-1.0"
    assert record["model"] == SAM_MODEL_ID == "sam-3.1"
    assert record["provider_mode"] == "replay"
    assert record["phrase"] == "water puddle"
    assert len(record["boxes"]) == 1


def test_observation_line_helpers():
    assert observation_line("water puddle") == WATER_LINE
    assert observation_line("frost") == "visual observation: frost detected (synthetic image)"
    assert "not an all-clear" in no_detection_line("water puddle")


def test_water_low_temp_is_at_risk_citing_visual_line():
    scenario = load_scenario(SCENARIOS / "visual_water_low_temp_v1")
    assert scenario.visual["object_count"] == 1
    result = compute_readiness(build_evidence_pack(scenario, AT_1800), AT_1800)
    assert result["status"] == "at_risk"
    assert WATER_LINE in result["reasons"]


def test_visual_only_water_with_unknown_temp_is_at_risk_not_guarantee():
    scenario = load_scenario(SCENARIOS / "visual_water_low_temp_v1")
    stripped = replace(scenario, records=[r for r in scenario.records if r.quantity != "indoor_temp"])
    assert stripped.visual is not None
    result = compute_readiness(build_evidence_pack(stripped, AT_1800), AT_1800)
    assert result["status"] == "at_risk"
    assert WATER_LINE in result["reasons"]
    assert result["status"] != "on_track"


def test_frost_missed_zero_objects_keeps_at_risk():
    scenario = load_scenario(SCENARIOS / "visual_frost_missed_v1")
    assert scenario.visual["object_count"] == 0
    result = compute_readiness(build_evidence_pack(scenario, AT_1800), AT_1800)
    assert result["status"] == "at_risk"
    assert no_detection_line("frost") in result["reasons"]


def test_dry_floor_zero_objects_never_on_track():
    scenario = load_scenario(SCENARIOS / "visual_dry_floor_v1")
    assert scenario.visual["object_count"] == 0
    result = compute_readiness(build_evidence_pack(scenario, AT_1800), AT_1800)
    assert result["status"] == "at_risk"
    assert "absence of a detection is not an all-clear" in " ".join(result["reasons"])


def test_cancelled_trip_with_water_detection_stays_cannot_tell():
    water = load_scenario(SCENARIOS / "visual_water_low_temp_v1")
    cancelled = replace(load_scenario(SCENARIOS / "demo_cancelled_v1"), visual=water.visual)
    result = compute_readiness(build_evidence_pack(cancelled, AT_1800), AT_1800)
    assert result["status"] == "cannot_tell"


def test_conflicting_indoor_with_water_detection_stays_cannot_tell():
    from aria_home.contracts import EvidenceRecord

    scenario = load_scenario(SCENARIOS / "visual_water_low_temp_v1")
    latest = next(r for r in scenario.records if r.id == "tstat-temp-1755")
    clash = EvidenceRecord.model_validate({**latest.model_dump(), "id": "tstat-temp-1755-clash", "value": 80.0})
    conflicted = replace(scenario, records=[*scenario.records, clash])
    result = compute_readiness(build_evidence_pack(conflicted, AT_1800), AT_1800)
    assert result["status"] == "cannot_tell"


def test_visual_never_verifies_recovery():
    for name in ("visual_water_low_temp_v1", "visual_frost_missed_v1", "visual_dry_floor_v1"):
        scenario = load_scenario(SCENARIOS / name)
        followup = follow_up_for(scenario, "inv-visual", AT_1800)
        stage = verify_recovery(scenario, followup, AT_1800)["stage"]
        assert stage not in ("warming_observed", "goal_verified", "arrival_met")


def test_hvac_payload_carries_line_not_image_data():
    scenario = load_scenario(SCENARIOS / "visual_water_low_temp_v1")
    result = compute_readiness(build_evidence_pack(scenario, AT_1800), AT_1800)
    payload = build_payload(
        "hvac_company",
        readiness=result,
        context=context_as_of(scenario, AT_1800),
        events=[],
        now=AT_1800,
        scenario=scenario,
    )
    observations = payload["relevant_observations"]
    assert WATER_LINE in observations
    dumped = json.dumps(payload)
    for token in ("webp", "base64", "data:image", "image_url", "mask", "box;x1"):
        assert token not in dumped


def test_whatsapp_text_carries_line_not_image_data():
    scenario = load_scenario(SCENARIOS / "visual_water_low_temp_v1")
    result = compute_readiness(build_evidence_pack(scenario, AT_1800), AT_1800)
    payload = build_payload(
        "hvac_company",
        readiness=result,
        context=context_as_of(scenario, AT_1800),
        events=[],
        now=AT_1800,
        scenario=scenario,
    )
    text = build_hvac_whatsapp_text(payload)
    assert WATER_LINE in text
    for token in ("webp", "base64", "data:image", "image_url"):
        assert token not in text


class _FakeHttp:
    def __init__(self, status=200, payload=None):
        self.calls = []
        self.status = status
        self.payload = payload

    def __call__(self, url, headers, body):
        self.calls.append({"url": url, "headers": headers, "body": body})
        return self.status, self.payload


def _refused():
    def explode(url, headers, body):
        raise AssertionError("live visual provider must not be called without opt-in")

    return explode


def test_live_refused_without_opt_in():
    provider = SamLiveProvider(config=VisualConfig.from_env({}))
    assert provider.mode == "disabled"
    with pytest.raises(RuntimeError):
        provider.segment(b"fake-image-bytes", "water puddle", http_post=_refused())
    with pytest.raises(RuntimeError):
        provider.observe(
            b"fake-image-bytes",
            "water puddle",
            "v1-water-floor",
            observed_at="2026-01-16T17:56:00-05:00",
            received_at="2026-01-16T17:56:30-05:00",
            http_post=_refused(),
        )


def test_live_rejects_non_sam_model_id():
    with pytest.raises(ValueError):
        VisualConfig.from_env({"ARIA_HOME_VISUAL_MODEL_ID": "other-model"})


def test_live_works_with_opt_in_and_fake_http():
    env = {"ARIA_HOME_VISUAL_LIVE": "1", "MODEL_API_KEY": "test-key"}
    provider = SamLiveProvider(config=VisualConfig.from_env(env))
    assert provider.mode == "live"
    recorded = json.loads(_recording("v1-water-floor"))
    fake = _FakeHttp(payload=recorded)
    observation = provider.observe(
        b"fake-image-bytes",
        "water puddle",
        "v1-water-floor",
        observed_at="2026-01-16T17:56:00-05:00",
        received_at="2026-01-16T17:56:30-05:00",
        http_post=fake,
    )
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["url"].endswith("/v1/responses")
    assert call["headers"]["Authorization"] == "Bearer test-key"
    assert call["body"]["model"] == "sam-3.1"
    assert call["body"]["metadata"] == {"mask_encoding": "one_bit"}
    content = call["body"]["input"][0]["content"]
    assert content[0] == {"type": "input_text", "text": "water puddle"}
    assert content[1]["image_url"].startswith("data:image/webp;base64,")
    record = observation.as_dict()
    assert record["provider_mode"] == "live"
    assert record["object_count"] == 1
    assert record["model"] == "sam-3.1"


def test_api_visual_metadata_image_and_gating():
    client = create_app().test_client()
    resp = client.get("/api/visual?scenario=visual_water_low_temp_v1&at=2026-01-16T18:00:00-05:00")
    assert resp.status_code == 200
    body = resp.get_json()
    visual = body["visual"]
    assert visual["image_id"] == "v1-water-floor"
    assert len(visual["boxes"]) == 1
    assert visual["caption"] == "Synthetic camera frame (muse-image-1.0) - segmentation by sam-3.1 (recorded)"
    assert visual["image_url"].startswith("/api/visual/image?")
    assert "base64" not in resp.get_data(as_text=True)

    image = client.get(visual["image_url"])
    assert image.status_code == 200
    assert image.content_type == "image/webp"
    assert len(image.data) > 0

    early = client.get("/api/visual?scenario=visual_water_low_temp_v1&at=2026-01-16T17:00:00-05:00")
    assert early.get_json()["visual"] is None
    early_image = client.get("/api/visual/image?scenario=visual_water_low_temp_v1&at=2026-01-16T17:00:00-05:00")
    assert early_image.status_code == 404

    none = client.get("/api/visual?scenario=demo_v1&at=2026-01-16T18:00:00-05:00")
    assert none.get_json()["visual"] is None
    unknown = client.get("/api/visual?scenario=no_such_scenario")
    assert unknown.status_code == 404


CARE_SPECS = (
    ("care/care-v1-window-frost", "frost"),
    ("care/care-v2-furnace-off", "indicator light"),
    ("care/care-v3-thermostat-blank", "blank display"),
    ("care/care-v4-pipe-frost", "frost"),
    ("care/care-v5-dry-floor", "water puddle"),
    ("care/care-v6-warm-morning", "frost"),
)

CARE_CAPTION = "Synthetic camera frame (muse-image-1.0) - segmentation by sam-3.1 (recorded)"


def test_care_recordings_replay_counts():
    provider = ReplayVisualProvider()
    counts = [
        provider.observe(
            image_id,
            phrase,
            observed_at="2026-01-17T02:30:00-05:00",
            received_at="2026-01-17T02:30:30-05:00",
            file=f"{image_id}.webp",
        ).object_count
        for image_id, phrase in CARE_SPECS
    ]
    assert counts == [0, 0, 1, 0, 0, 0]


def _care_visual_at(stamp):
    scenario = load_scenario(SCENARIOS / "care_home_v1")
    return visual_as_of(scenario, datetime.fromisoformat(stamp))


def test_care_frames_visible_at_story_times():
    assert _care_visual_at("2026-01-16T19:20:00-05:00") is None
    assert _care_visual_at("2026-01-17T02:31:00-05:00")["image_id"] == "care/care-v1-window-frost"
    assert _care_visual_at("2026-01-17T02:45:00-05:00")["image_id"] == "care/care-v2-furnace-off"
    assert _care_visual_at("2026-01-17T04:21:00-05:00")["image_id"] == "care/care-v3-thermostat-blank"
    assert _care_visual_at("2026-01-17T04:51:00-05:00")["image_id"] == "care/care-v4-pipe-frost"
    assert _care_visual_at("2026-01-17T06:21:00-05:00")["image_id"] == "care/care-v5-dry-floor"
    assert _care_visual_at("2026-01-17T06:45:00-05:00")["image_id"] == "care/care-v6-warm-morning"
    assert _care_visual_at("2026-01-17T07:01:00-05:00")["image_id"] == "care/care-v6-warm-morning"


def test_care_misses_flagged_and_keep_at_risk():
    scenario = load_scenario(SCENARIOS / "care_home_v1")
    assert len(scenario.visuals) == 6
    assert scenario.visual is None
    for stamp in ("2026-01-17T02:31:00-05:00", "2026-01-17T04:51:00-05:00"):
        at = datetime.fromisoformat(stamp)
        pack = build_evidence_pack(scenario, at)
        assert pack["visual_evidence"]["known_miss"] is True
        assert pack["visual_evidence"]["object_count"] == 0
        result = compute_readiness(pack, at)
        assert result["status"] == "at_risk"
        assert no_detection_line("frost") in result["reasons"]


def test_care_visual_never_decides_or_verifies():
    scenario = load_scenario(SCENARIOS / "care_home_v1")
    expected = {
        "2026-01-17T02:31:00-05:00": ("at_risk", "telemetry_missing"),
        "2026-01-17T04:21:00-05:00": ("at_risk", "reporting_restored"),
        "2026-01-17T04:51:00-05:00": ("at_risk", "warming_observed"),
        "2026-01-17T06:21:00-05:00": ("on_track", "goal_verified"),
        "2026-01-17T07:01:00-05:00": ("arrival_passed", "arrival_met"),
    }
    created = datetime.fromisoformat("2026-01-17T02:31:00-05:00")
    followup = follow_up_for(scenario, "inv-care-visual", created)
    for stamp, (status, stage) in expected.items():
        at = datetime.fromisoformat(stamp)
        assert compute_readiness(build_evidence_pack(scenario, at), at)["status"] == status
        assert verify_recovery(scenario, followup, at)["stage"] == stage
    late = datetime.fromisoformat("2026-01-17T06:21:00-05:00")
    stripped = replace(scenario, records=[r for r in scenario.records if r.quantity != "indoor_temp"])
    assert stripped.visuals
    assert compute_readiness(build_evidence_pack(stripped, late), late)["status"] != "on_track"


def test_care_hvac_payload_carries_line_not_image():
    scenario = load_scenario(SCENARIOS / "care_home_v1")
    at = datetime.fromisoformat("2026-01-17T02:45:00-05:00")
    result = compute_readiness(build_evidence_pack(scenario, at), at)
    payload = build_payload(
        "hvac_company",
        readiness=result,
        context=context_as_of(scenario, at),
        events=[],
        now=at,
        scenario=scenario,
    )
    assert any("visual observation" in line for line in payload["relevant_observations"])
    dumped = json.dumps(payload)
    for token in ("webp", "base64", "data:image", "image_url", "mask", "box;x1"):
        assert token not in dumped


def test_care_api_visual_caption_image_and_gating():
    client = create_app().test_client()
    resp = client.get("/api/visual?scenario=care_home_v1&at=2026-01-17T02:31:00-05:00")
    assert resp.status_code == 200
    visual = resp.get_json()["visual"]
    assert visual["image_id"] == "care/care-v1-window-frost"
    assert visual["object_count"] == 0
    assert visual["known_miss"] is True
    assert visual["caption"] == CARE_CAPTION
    assert visual["image_url"].startswith("/api/visual/image?")
    assert "base64" not in resp.get_data(as_text=True)

    image = client.get(visual["image_url"])
    assert image.status_code == 200
    assert image.content_type == "image/webp"
    assert image.data == (FIXTURES_DIR / "care" / "care-v1-window-frost.webp").read_bytes()

    morning = client.get("/api/visual?scenario=care_home_v1&at=2026-01-17T07:01:00-05:00").get_json()["visual"]
    assert morning["image_id"] == "care/care-v6-warm-morning"
    assert "known_miss" not in morning
    assert client.get(morning["image_url"]).status_code == 200

    evening = client.get("/api/visual?scenario=care_home_v1&at=2026-01-16T19:20:00-05:00")
    assert evening.get_json()["visual"] is None


def test_sam_live_request_carries_no_max_tokens():
    provider = SamLiveProvider(config=VisualConfig.from_env({"ARIA_HOME_VISUAL_LIVE": "1", "MODEL_API_KEY": "test-key"}))
    request = provider.build_request(b"fake-image-bytes", "water puddle")
    assert request["url"].endswith("/v1/responses")
    assert "max_tokens" not in request["body"]
    assert "max_output_tokens" not in request["body"]
