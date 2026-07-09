"""Tests for bot.config_loader — validation and threshold logic (pure, no I/O)."""

import copy
import pytest

from bot import config_loader
from bot.config_loader import (
    validate_config,
    validate_treasure_hunt,
    meets_loot_threshold,
)


def _valid_config():
    return {
        "timings": {k: 1 for k in config_loader.REQUIRED_TIMINGS},
        "camera": {"start": [1, 2], "end": [3, 4]},
        "deploy": {
            "troops": [
                {"type": "drag", "slot": [1, 2], "drag_start": [3, 4], "drag_end": [5, 6]},
                {"type": "click", "slot": [1, 2], "target": [3, 4]},
            ],
            "heroes": [{"slot": [1, 2], "target": [3, 4]}],
            "spells": [{"slot": [1, 2], "target": [3, 4]}],
            "hero_abilities": [[1, 2]],
        },
        "thresholds": {10: {"gold_elixir_total": 600000, "dark_elixir": 2000}},
        "detection": {k: 1 for k in config_loader.REQUIRED_DETECTION},
    }


# --- validate_config ---------------------------------------------------------

def test_valid_config_has_no_errors():
    assert validate_config(_valid_config()) == []


def test_missing_section_reported():
    cfg = _valid_config()
    del cfg["camera"]
    errors = validate_config(cfg)
    assert any("camera" in e for e in errors)


def test_missing_detection_key_reported():
    cfg = _valid_config()
    del cfg["detection"]["battle_end_timeout"]
    errors = validate_config(cfg)
    assert any("battle_end_timeout" in e for e in errors)


def test_negative_detection_value_reported():
    cfg = _valid_config()
    cfg["detection"]["poll_interval"] = -1
    errors = validate_config(cfg)
    assert any("poll_interval" in e for e in errors)


def test_non_numeric_timing_reported():
    cfg = _valid_config()
    cfg["timings"]["scout_wait"] = "fast"
    errors = validate_config(cfg)
    assert any("scout_wait" in e for e in errors)


def test_bad_camera_shape_reported():
    cfg = _valid_config()
    cfg["camera"]["start"] = [1, 2, 3]
    errors = validate_config(cfg)
    assert any("camera.start" in e for e in errors)


def test_drag_troop_missing_field_reported():
    cfg = _valid_config()
    del cfg["deploy"]["troops"][0]["drag_end"]
    errors = validate_config(cfg)
    assert any("drag_end" in e for e in errors)


# --- meets_loot_threshold ----------------------------------------------------

@pytest.fixture
def config():
    return _valid_config()


def test_meets_threshold_via_dark_elixir(config):
    loot = {"gold": 0, "elixir": 0, "dark_elixir": 2500}
    assert meets_loot_threshold(10, loot, config) is True


def test_meets_threshold_via_gold_elixir_total(config):
    loot = {"gold": 400000, "elixir": 300000, "dark_elixir": 0}
    assert meets_loot_threshold(10, loot, config) is True


def test_below_threshold(config):
    loot = {"gold": 100000, "elixir": 100000, "dark_elixir": 100}
    assert meets_loot_threshold(10, loot, config) is False


def test_unknown_townhall_level_is_false(config):
    loot = {"gold": 9_000_000, "elixir": 9_000_000, "dark_elixir": 9_000_000}
    assert meets_loot_threshold(99, loot, config) is False


# --- validate_treasure_hunt --------------------------------------------------

def _valid_treasure_hunt():
    return {
        "treasure_hunt": {
            "claim_button": [1, 2],
            "final_click": [3, 4],
            "advanced_clicks": [[1, 2], [3, 4]],
            "final_click_delay": 4,
        }
    }


def test_valid_treasure_hunt_has_no_errors():
    assert validate_treasure_hunt(_valid_treasure_hunt()) == []


def test_treasure_hunt_missing_section():
    errors = validate_treasure_hunt({})
    assert len(errors) == 1


def test_treasure_hunt_bad_advanced_clicks():
    cfg = _valid_treasure_hunt()
    cfg["treasure_hunt"]["advanced_clicks"] = [[1, 2, 3]]
    errors = validate_treasure_hunt(cfg)
    assert any("advance" in e for e in errors)


def test_treasure_hunt_bad_final_click_delay():
    cfg = _valid_treasure_hunt()
    cfg["treasure_hunt"]["final_click_delay"] = -1
    errors = validate_treasure_hunt(cfg)
    assert any("final_click_delay" in e for e in errors)


def test_treasure_hunt_bad_claim_button_shape():
    cfg = _valid_treasure_hunt()
    cfg["treasure_hunt"]["claim_button"] = [1]
    errors = validate_treasure_hunt(cfg)
    assert any("claim_button" in e for e in errors)
