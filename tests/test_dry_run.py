"""Tests for bot.dry_run — the DryRunActions shim used by --dry-run."""

import re
from pathlib import Path

from bot import actions
from bot.dry_run import DryRunActions

_STATE_MACHINE = Path(__file__).resolve().parent.parent / "bot" / "state_machine.py"


def _called_action_names():
    source = _STATE_MACHINE.read_text()
    return set(re.findall(r"actions\.([a-z_]+)", source))


def test_shim_covers_every_action_used_by_state_machine():
    shim = DryRunActions()
    for name in _called_action_names():
        assert callable(getattr(shim, name, None)), f"DryRunActions missing '{name}'"


def test_mutating_calls_are_noops():
    shim = DryRunActions()
    assert shim.click_attack_button(1, 2) is None
    assert shim.deploy_troop_drag(troop_slot=(1, 2)) is None


def test_wait_delegates_to_real_actions(monkeypatch):
    calls = []
    monkeypatch.setattr(actions, "wait", lambda s: calls.append(s))
    DryRunActions().wait(7)
    assert calls == [7]
