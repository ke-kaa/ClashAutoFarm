"""Tests for bot.state_machine — transitions and the tick-driven attack timeline."""

import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bot import state_machine
from bot.state_machine import StateMachine, State


def _config():
    return {
        "timings": {
            "troop_engage_wait": 10,
            "hero_ability_activate_after_deployment": 15,
            "scout_wait": 6,
            "reconnect_wait": 10,
            "result_screen_wait": 14,
        },
        "detection": {
            "scout_screen_timeout": 12,
            "battle_end_timeout": 120,
            "home_screen_timeout": 20,
            "poll_interval": 0.5,
        },
        "camera": {"start": [1, 2], "end": [3, 4]},
        "deploy": {"troops": [], "heroes": [], "spells": [], "hero_abilities": []},
        "regions": {},
        "thresholds": {10: {"gold_elixir_total": 600000, "dark_elixir": 2000}},
        "army_training": {"recipes_tab": [1, 2], "use_recipe_button": [3, 4]},
        "accounts": {
            "settings_button": [1, 1],
            "switch_button": [2, 2],
            "card_region": [10, 100, 400, 500],
            "reload_wait": 20,
            "max_scrolls": 3,
            "scroll_drag": [1, 2, 3, 4],
            "rotation": [
                {"name": "GuardianDeity0", "townhall_level": 11},
                {"name": "GuardianDeityI", "townhall_level": 13},
            ],
        },
        "treasure_hunt": {
            "claim_button": [1, 2],
            "advanced_clicks": [[1, 1]],
            "final_click_delay": 4,
            "final_click": [3, 4],
        },
    }


@pytest.fixture
def machine(monkeypatch):
    monkeypatch.setattr(state_machine, "load_config", _config)
    monkeypatch.setattr(state_machine, "actions", MagicMock())
    monkeypatch.setattr(state_machine, "tmpl", MagicMock())
    monkeypatch.setattr(state_machine, "grab", lambda: "SCREEN")
    m = StateMachine(templates_dict={}, townhall_level=10, csv_writer=MagicMock())
    return m


SCREEN = "SCREEN"


# --- transitions / timeout ---------------------------------------------------

def test_transition_updates_state_and_timer(machine):
    before = machine._state_entered_at
    time.sleep(0.01)
    machine.transition(State.SCOUTING)
    assert machine.state == State.SCOUTING
    assert machine._state_entered_at > before


def test_check_timeout_recovers_to_idle(machine, monkeypatch):
    monkeypatch.setattr(machine, "_dump_failure_screenshot", MagicMock())
    machine.state = State.ATTACKING
    machine._state_entered_at = time.time() - 10_000
    assert machine._check_timeout(SCREEN) is True
    assert machine.state == State.IDLE
    machine._dump_failure_screenshot.assert_called_once()


# --- idle / auto-train -------------------------------------------------------

def test_idle_uses_army_recipe_once(machine):
    machine._handle_idle()
    assert machine.state == State.FINDING_MATCH
    assert machine._army_recipe_used is True
    state_machine.actions.use_army_recipe.assert_called_once()


def test_idle_skips_recipe_after_first_use(machine):
    machine._army_recipe_used = True
    machine._handle_idle()
    state_machine.actions.use_army_recipe.assert_not_called()


# --- finding match -----------------------------------------------------------

def test_finding_match_success(machine, monkeypatch):
    monkeypatch.setattr(machine, "_wait_for", lambda *a, **k: (True, SCREEN))
    machine.state = State.FINDING_MATCH
    machine._handle_finding_match()
    assert machine.state == State.SCOUTING


def test_finding_match_timeout_bails_to_idle(machine, monkeypatch):
    monkeypatch.setattr(machine, "_wait_for", lambda *a, **k: (False, SCREEN))
    machine.state = State.FINDING_MATCH
    machine._handle_finding_match()
    assert machine.state == State.IDLE


# --- scouting ----------------------------------------------------------------

def test_scouting_meets_threshold_attacks(machine, monkeypatch):
    monkeypatch.setattr(state_machine, "read_loot",
                        lambda s, r: {"gold": 1, "elixir": 1, "dark_elixir": 1})
    monkeypatch.setattr(state_machine, "meets_loot_threshold", lambda *a: True)
    started = MagicMock()
    monkeypatch.setattr(machine, "_start_attack", started)
    machine._handle_scouting(SCREEN)
    started.assert_called_once()


def test_scouting_below_threshold_skips(machine, monkeypatch):
    monkeypatch.setattr(state_machine, "read_loot",
                        lambda s, r: {"gold": 1, "elixir": 1, "dark_elixir": 1})
    monkeypatch.setattr(state_machine, "meets_loot_threshold", lambda *a: False)
    started = MagicMock()
    monkeypatch.setattr(machine, "_start_attack", started)
    machine._handle_scouting(SCREEN)
    started.assert_not_called()
    state_machine.actions.click_next.assert_called_once()


def test_scouting_ocr_failure_attacks_anyway(machine, monkeypatch):
    monkeypatch.setattr(state_machine, "read_loot",
                        lambda s, r: {"gold": -1, "elixir": 1, "dark_elixir": 1})
    started = MagicMock()
    monkeypatch.setattr(machine, "_start_attack", started)
    machine._handle_scouting(SCREEN)
    started.assert_called_once()


# --- tick-driven attack timeline ---------------------------------------------

def test_start_attack_enters_engage_phase(machine):
    machine._start_attack()
    assert machine.state == State.ATTACKING
    assert machine._attack_phase == "engage_wait"
    assert machine._phase_deadline > time.time()


def test_attacking_holds_until_engage_deadline(machine, monkeypatch):
    spells = MagicMock()
    monkeypatch.setattr(machine, "_deploy_spells", spells)
    machine._attack_phase = "engage_wait"
    machine._phase_deadline = time.time() + 1000
    machine._handle_attacking(SCREEN)
    assert machine._attack_phase == "engage_wait"
    spells.assert_not_called()


def test_attacking_engage_advances_to_ability(machine, monkeypatch):
    spells = MagicMock()
    monkeypatch.setattr(machine, "_deploy_spells", spells)
    machine._attack_phase = "engage_wait"
    machine._phase_deadline = time.time() - 1
    machine._handle_attacking(SCREEN)
    spells.assert_called_once()
    assert machine._attack_phase == "ability_wait"
    assert machine._phase_deadline > time.time()


def test_attacking_ability_advances_to_await_end(machine, monkeypatch):
    abilities = MagicMock()
    monkeypatch.setattr(machine, "_activate_abilities", abilities)
    machine._attack_phase = "ability_wait"
    machine._phase_deadline = time.time() - 1
    machine._handle_attacking(SCREEN)
    abilities.assert_called_once()
    assert machine._attack_phase == "await_end"


def test_attacking_await_end_transitions_when_battle_over(machine):
    machine.state = State.ATTACKING
    machine._attack_phase = "await_end"
    machine.attack_start_time = time.time()
    state_machine.tmpl.is_battle_over.return_value = True
    state_machine.tmpl.is_claim_reward.return_value = False
    machine._handle_attacking(SCREEN)
    assert machine.state == State.BATTLE_END
    assert machine.total_attacked == 1


def test_attacking_await_end_transitions_on_claim_reward(machine):
    machine.state = State.ATTACKING
    machine._attack_phase = "await_end"
    machine.attack_start_time = time.time()
    state_machine.tmpl.is_battle_over.return_value = False
    state_machine.tmpl.is_claim_reward.return_value = True
    machine._handle_attacking(SCREEN)
    assert machine.state == State.BATTLE_END


def test_attacking_await_end_stays_when_not_over(machine):
    machine.state = State.ATTACKING
    machine._attack_phase = "await_end"
    machine.attack_start_time = time.time()
    state_machine.tmpl.is_battle_over.return_value = False
    state_machine.tmpl.is_claim_reward.return_value = False
    machine._handle_attacking(SCREEN)
    assert machine.state == State.ATTACKING


# --- battle end --------------------------------------------------------------

def test_battle_end_normal_returns_home(machine, monkeypatch):
    machine.treasure_hunt = False
    monkeypatch.setattr(machine, "_wait_for", lambda *a, **k: (True, SCREEN))
    machine.state = State.BATTLE_END
    machine._handle_battle_end()
    state_machine.actions.return_home.assert_called_once()
    assert machine.state == State.IDLE


def test_battle_end_claims_reward_when_chest_present(machine, monkeypatch):
    machine.treasure_hunt = True
    monkeypatch.setattr(machine, "_wait_for", lambda *a, **k: (True, SCREEN))
    state_machine.tmpl.is_claim_reward.return_value = True
    machine.state = State.BATTLE_END
    machine._handle_battle_end()
    state_machine.actions.claim_treasure_reward.assert_called_once()
    state_machine.actions.return_home.assert_not_called()
    assert machine.state == State.IDLE


def test_reconnected_home_confirmed_goes_idle(machine):
    machine.state = State.DISCONNECTED
    state_machine.tmpl.is_home_screen.return_value = True
    machine._handle_reconnected(SCREEN)
    assert machine.state == State.IDLE


def test_reconnected_not_home_stays(machine):
    machine.state = State.DISCONNECTED
    state_machine.tmpl.is_home_screen.return_value = False
    machine._handle_reconnected(SCREEN)
    assert machine.state == State.DISCONNECTED


def test_battle_end_returns_home_when_no_chest(machine, monkeypatch):
    machine.treasure_hunt = True
    monkeypatch.setattr(machine, "_wait_for", lambda *a, **k: (True, SCREEN))
    state_machine.tmpl.is_claim_reward.return_value = False
    machine.state = State.BATTLE_END
    machine._handle_battle_end()
    state_machine.actions.claim_treasure_reward.assert_not_called()
    state_machine.actions.return_home.assert_called_once()


def _limits(max_attacks=0, max_runtime=0, max_loot=False, switch_when_full=False):
    return SimpleNamespace(
        account_name="x",
        max_attacks=max_attacks,
        max_runtime=max_runtime,
        max_loot=max_loot,
        switch_when_full=switch_when_full,
    )


def test_battle_end_stops_when_storage_full(machine, monkeypatch):
    monkeypatch.setattr(machine, "_wait_for", lambda *a, **k: (True, SCREEN))
    monkeypatch.setattr(state_machine, "read_loot", lambda s, r: {"gold": 1, "elixir": 1, "dark_elixir": 1})
    monkeypatch.setattr(state_machine, "check_storage_full", lambda *a: True)
    machine.treasure_hunt = False
    machine.stop_event = MagicMock()
    machine.args = _limits(max_loot=True)
    machine.state = State.BATTLE_END
    machine._handle_battle_end()
    machine.stop_event.set.assert_called_once()


def test_battle_end_no_stop_when_storage_not_full(machine, monkeypatch):
    monkeypatch.setattr(machine, "_wait_for", lambda *a, **k: (True, SCREEN))
    monkeypatch.setattr(state_machine, "read_loot", lambda s, r: {"gold": 1, "elixir": 1, "dark_elixir": 1})
    monkeypatch.setattr(state_machine, "check_storage_full", lambda *a: False)
    machine.treasure_hunt = False
    machine.stop_event = MagicMock()
    machine.args = _limits(max_loot=True)
    machine.state = State.BATTLE_END
    machine._handle_battle_end()
    machine.stop_event.set.assert_not_called()


# --- account switching -------------------------------------------------------

def _switch_ready(machine):
    machine.stop_event = MagicMock()


def test_battle_end_switches_when_full_and_more_accounts(machine, monkeypatch):
    monkeypatch.setattr(machine, "_wait_for", lambda *a, **k: (True, SCREEN))
    monkeypatch.setattr(state_machine, "read_loot", lambda s, r: {"gold": 1, "elixir": 1, "dark_elixir": 1})
    monkeypatch.setattr(state_machine, "check_storage_full", lambda *a: True)
    machine.treasure_hunt = False
    _switch_ready(machine)
    machine.args = _limits(switch_when_full=True)
    machine._rotation_idx = 0
    machine.state = State.BATTLE_END
    machine._handle_battle_end()
    assert machine.state == State.SWITCHING_ACCOUNT
    machine.stop_event.set.assert_not_called()


def test_battle_end_stops_when_full_on_last_account(machine, monkeypatch):
    monkeypatch.setattr(machine, "_wait_for", lambda *a, **k: (True, SCREEN))
    monkeypatch.setattr(state_machine, "read_loot", lambda s, r: {"gold": 1, "elixir": 1, "dark_elixir": 1})
    monkeypatch.setattr(state_machine, "check_storage_full", lambda *a: True)
    machine.treasure_hunt = False
    _switch_ready(machine)
    machine.args = _limits(switch_when_full=True)
    machine._rotation_idx = 1  # last of two accounts
    machine.state = State.BATTLE_END
    machine._handle_battle_end()
    machine.stop_event.set.assert_called_once()


def test_begin_switch_advances_and_enters_state(machine):
    machine._begin_switch()
    assert machine.state == State.SWITCHING_ACCOUNT
    assert machine._rotation_idx == 1
    assert machine._switch_phase == "open"


def test_switch_open_opens_menu(machine):
    _switch_ready(machine)
    machine._rotation_idx = 1
    machine._switch_phase = "open"
    machine._handle_switching_account(SCREEN)
    state_machine.actions.open_account_menu.assert_called_once()
    assert machine._switch_phase == "await_card"


def test_switch_selects_when_name_located(machine, monkeypatch):
    _switch_ready(machine)
    machine._rotation_idx = 1  # target "GuardianDeityI"
    machine._switch_phase = "select"
    machine._switch_scrolls = 0
    monkeypatch.setattr(state_machine, "locate_text", lambda s, region, target: (120, 260))
    machine._handle_switching_account(SCREEN)
    state_machine.actions.click.assert_called_with(120, 260)
    assert machine._switch_phase == "reload"


def test_switch_scrolls_when_name_not_found(machine, monkeypatch):
    _switch_ready(machine)
    machine._rotation_idx = 1
    machine._switch_phase = "select"
    machine._switch_scrolls = 0
    monkeypatch.setattr(state_machine, "locate_text", lambda s, region, target: None)
    machine._handle_switching_account(SCREEN)
    state_machine.actions.scroll_card.assert_called_once()
    assert machine._switch_scrolls == 1
    assert machine._switch_phase == "select"


def test_switch_stops_when_not_found_after_max_scrolls(machine, monkeypatch):
    _switch_ready(machine)
    machine._rotation_idx = 1
    machine._switch_phase = "select"
    machine._switch_scrolls = 3  # == max_scrolls
    monkeypatch.setattr(state_machine, "locate_text", lambda s, region, target: None)
    machine._handle_switching_account(SCREEN)
    machine.stop_event.set.assert_called_once()


def test_switch_verify_home_resets_and_goes_idle(machine):
    _switch_ready(machine)
    machine._rotation_idx = 1
    machine._switch_phase = "verify"
    machine._army_recipe_used = True
    state_machine.tmpl.is_home_screen.return_value = True
    machine._handle_switching_account(SCREEN)
    assert machine.state == State.IDLE
    assert machine.current_account_name == "GuardianDeityI"
    assert machine.townhall_level == 13  # updated to the switched-in account's TH
    assert machine._army_recipe_used is False


def test_switch_verify_fail_stops(machine):
    _switch_ready(machine)
    machine._rotation_idx = 1
    machine._switch_phase = "verify"
    state_machine.tmpl.is_home_screen.return_value = False
    machine._handle_switching_account(SCREEN)
    machine.stop_event.set.assert_called_once()
