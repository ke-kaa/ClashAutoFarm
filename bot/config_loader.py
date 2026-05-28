"""
bot/config_loader.py — Load and validate config.yaml.
"""

import yaml
from pathlib import Path


_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(path=None):
    """Load config.yaml and return the parsed dict."""
    config_path = Path(path) if path else _CONFIG_PATH
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def meets_loot_threshold(townhall_level, loot):
    """
    Check if loot meets the minimum threshold for a given townhall level.

    Parameters
    ----------
    townhall_level : int
    loot : dict with keys 'gold', 'elixir', 'dark_elixir' (int values)

    Returns
    -------
    bool
    """
    config = load_config()
    th = config["thresholds"].get(townhall_level)
    if not th:
        return False

    if loot["dark_elixir"] >= th["dark_elixir"]:
        return True

    return (loot["gold"] + loot["elixir"]) >= th["gold_elixir_total"]
