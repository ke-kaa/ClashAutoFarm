"""
bot/config_loader.py — Load and validate config.yaml.
"""

import sys
import yaml
from pathlib import Path
from loguru import logger

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

REQUIRED_TIMINGS = [
    "scout_wait",
    "attack_duration",
    "reconnect_wait",
    "match_wait",
    "troop_engage_wait",
    "hero_ability_activate_after_deployment",
    "result_screen_wait",
]

REQUIRED_DETECTION = [
    "scout_screen_timeout",
    "battle_end_timeout",
    "home_screen_timeout",
    "poll_interval",
]

REQUIRED_SECTIONS = ["timings", "deploy", "camera", "thresholds", "detection", "army_training"]


def load_config(path=None):
    """Load config.yaml and return the parsed dict."""
    config_path = Path(path) if path else _CONFIG_PATH
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def validate_config(config):
    """
    Validate config structure and values on startup.
    Returns a list of error strings. Empty list means valid.
    """
    errors = []

    for section in REQUIRED_SECTIONS:
        if section not in config:
            errors.append(f"Missing required section: '{section}'")

    if "timings" in config:
        timings = config["timings"]
        for key in REQUIRED_TIMINGS:
            if key not in timings:
                errors.append(f"Missing timing: '{key}'")
            elif not isinstance(timings[key], (int, float)) or timings[key] < 0:
                errors.append(
                    f"Timing '{key}' must be a positive number, got: {timings[key]}"
                )

    if "camera" in config:
        camera = config["camera"]
        for key in ["start", "end"]:
            if key not in camera:
                errors.append(f"Missing camera.{key}")
            elif not isinstance(camera[key], list) or len(camera[key]) != 2:
                errors.append(f"camera.{key} must be a list of [x, y]")

    if "deploy" in config:
        deploy = config["deploy"]
        for key in ["troops", "heroes", "spells", "hero_abilities"]:
            if key not in deploy:
                errors.append(f"Missing deploy.{key}")

        for i, troop in enumerate(deploy.get("troops", [])):
            if "type" not in troop:
                errors.append(f"deploy.troops[{i}] missing 'type'")
            if "slot" not in troop:
                errors.append(f"deploy.troops[{i}] missing 'slot'")
            if troop.get("type") == "drag":
                for field in ["drag_start", "drag_end"]:
                    if field not in troop:
                        errors.append(f"deploy.troops[{i}] (drag) missing '{field}'")
            elif troop.get("type") == "click":
                if "target" not in troop:
                    errors.append(f"deploy.troops[{i}] (click) missing 'target'")

    if "thresholds" in config:
        for level, th in config["thresholds"].items():
            if not isinstance(th, dict):
                errors.append(f"thresholds.{level} must be a dict")
                continue
            for key in ["gold_elixir_total", "dark_elixir"]:
                if key not in th:
                    errors.append(f"thresholds.{level} missing '{key}'")
                elif not isinstance(th[key], (int, float)) or th[key] < 0:
                    errors.append(f"thresholds.{level}.{key} must be a positive number")

    if "detection" in config:
        for key in REQUIRED_DETECTION:
            if key not in config["detection"].keys():
                errors.append(f"Missing detection: '{key}'")
        detection = config["detection"].items()
        for key, item in detection:
            if not isinstance(item, (int, float)) or item < 0:
                errors.append(f"detection.{key} must be a positive number")

    if "army_training" in config:
        army_training = config["army_training"]
        for key in ["recipes_tab", "use_recipe_button"]:
            if key not in army_training:
                errors.append(f"Missing army_training.{key}")
            elif not isinstance(army_training[key], list) or len(army_training[key]) != 2:
                errors.append(f"army_training.{key} must be a list of [x, y]")

    return errors


def load_and_validate(path=None):
    """Load config, validate it, and abort on errors."""
    config = load_config(path)
    errors = validate_config(config)

    if errors:
        logger.error("Config validation failed:")
        for err in errors:
            logger.error(f"  • {err}")
        sys.exit(1)

    logger.info("Config loaded and validated")
    return config


def meets_loot_threshold(townhall_level, loot, config):
    """Check if loot meets the minimum threshold for a given townhall level."""
    th = config["thresholds"].get(townhall_level)
    if not th:
        return False

    if loot["dark_elixir"] >= th["dark_elixir"]:
        return True

    return (loot["gold"] + loot["elixir"]) >= th["gold_elixir_total"]


def check_storage_full(townhall_level, loot, config):
    """Check if loot has reached the maximum threshold for a given townhall level."""
    th = config.get("storage_capacities", {}).get(townhall_level)
    if not th:
        return False

    return (
        loot["dark_elixir"] >= th["dark_elixir"]
        and loot["gold"] >= th["gold"]
        and loot["elixir"] >= th["elixir"]
    )


def validate_treasure_hunt(config):
    """Validate treasure_hunt section"""
    errors = []
    th = config.get("treasure_hunt", {})
    if not th:
        return ["--treasure-hunt set to true but config has no treasure_hunt session."]
    for key in ["claim_button", "final_click"]:
        if key not in th or not (isinstance(th[key], list) and len(th[key]) == 2):
            errors.append(f"treasure_hunt.{key}, must be a list")
    if not isinstance(th["advanced_clicks"], list) or not th["advanced_clicks"]:
        errors.append("treasure_hunt.advanced_clicks must be a list of [x, y]")
    else:
        for i, pos in enumerate(th["advanced_clicks"]):
            if not (isinstance(pos, list) and len(pos) == 2):
                errors.append(f"treasure_hunt.advance_clicks[{i}] must be [x, y]")
    d = th.get("final_click_delay")
    if not isinstance(d, (int, float)) or d < 0:
        errors.append("treasure_hunt.final_click_delay must be a positive number")
    return errors
