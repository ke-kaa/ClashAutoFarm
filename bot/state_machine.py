"""
bot/state_machine.py — Game state detection and transitions.
"""

import time
from enum import Enum, auto
from pathlib import Path
from loguru import logger

from bot import actions
from bot.config_loader import load_config, meets_loot_threshold
from vision.capture import grab, save_screenshot
from vision import templates as tmpl
from vision.ocr import read_loot


FAILURES_DIR = Path(__file__).resolve().parent.parent / "logs" / "failures"

STATE_TIMEOUTS = {
    "IDLE": 30,
    "FINDING_MATCH": 30,
    "SCOUTING": 60,
    "ATTACKING": 240,
    "BATTLE_END": 30,
    "DISCONNECTED": 120,
    "RECONNECT_POPUP": 60,
}


class State(Enum):
    IDLE = auto()
    FINDING_MATCH = auto()
    SCOUTING = auto()
    ATTACKING = auto()
    BATTLE_END = auto()
    DISCONNECTED = auto()
    RECONNECT_POPUP = auto()


class StateMachine:
    def __init__(self, templates_dict, townhall_level=10):
        self.state = State.IDLE
        self.templates = templates_dict
        self.townhall_level = townhall_level
        self.config = load_config()
        self._state_entered_at = time.time()

    def transition(self, new_state):
        """Transition to a new state."""
        logger.info("{} → {}", self.state.name, new_state.name)
        self.state = new_state
        self._state_entered_at = time.time()

    def _check_timeout(self, screen):
        """Check if current state has exceeded its timeout. Dump screenshot if so."""
        timeout = STATE_TIMEOUTS.get(self.state.name, 60)
        elapsed = time.time() - self._state_entered_at

        if elapsed > timeout:
            logger.warning(
                "Stuck in {} for {:.0f}s (limit {}s)", self.state.name, elapsed, timeout
            )
            self._dump_failure_screenshot(screen, reason="timeout")
            self.transition(State.IDLE)
            return True
        return False

    def _dump_failure_screenshot(self, screen, reason="unknown"):
        """Save a screenshot to logs/failures/ for debugging."""
        FAILURES_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{reason}_{self.state.name}_{timestamp}.png"
        path = FAILURES_DIR / filename
        save_screenshot(screen, str(path))
        logger.debug("Screenshot saved to {}", path)

    def tick(self):
        """Run one cycle of the state machine."""
        screen = grab()

        if self._check_timeout(screen):
            return

        if tmpl.is_disconnected(screen, self.templates):
            self.transition(State.DISCONNECTED)
            self._handle_disconnected()
            return

        if tmpl.is_reconnect_popup(screen, self.templates):
            self.transition(State.RECONNECT_POPUP)
            self._handle_reconnect()
            return

        if self.state == State.IDLE:
            self._handle_idle()
        elif self.state == State.FINDING_MATCH:
            self._handle_finding_match()
        elif self.state == State.SCOUTING:
            self._handle_scouting(screen)
        elif self.state == State.ATTACKING:
            self._handle_attacking()
        elif self.state == State.BATTLE_END:
            self._handle_battle_end()

    def _handle_idle(self):
        """IDLE → click attack → FINDING_MATCH."""
        actions.click_attack_button()
        actions.click_find_match()
        actions.click_confirm_attack()
        self.transition(State.FINDING_MATCH)

    def _handle_finding_match(self):
        """FINDING_MATCH → wait for match → SCOUTING."""
        det = self.config.get("detection", {})
        ok, _ = self._wait_for(lambda s: tmpl.is_onscout_screen(s, self.templates), timeout=det["scout_screen_timeout"], poll=det["poll_interval"])
        if ok:
            self.transition(State.SCOUTING)
        else: 
            logger.warning("Scout screen never appeare; bailing to IDLE")
            self.transition(State.IDLE)

    def _handle_scouting(self, screen):
        """SCOUTING → read loot → attack or skip."""
        regions = self.config.get("regions", {})
        loot = read_loot(screen, regions)
        logger.info(
            "Loot: gold={}  elixir={}  dark={}",
            loot["gold"],
            loot["elixir"],
            loot["dark_elixir"],
        )

        any_failed = -1 in loot.values()
        if any_failed:
            logger.warning("OCR failed on one or more values, attacking anyway")
            self._start_attack()
            return

        if meets_loot_threshold(self.townhall_level, loot):
            logger.info("Meets threshold — attacking")
            self._start_attack()
        else:
            logger.info("Below threshold — skipping")
            actions.click_next()
            actions.wait(self.config["timings"]["scout_wait"])

    def _start_attack(self):
        """Deploy troops and transition to ATTACKING."""
        self.transition(State.ATTACKING)
        deploy = self.config["deploy"]
        timings = self.config["timings"]
        camera = self.config["camera"]

        actions.zoom_in()
        actions.adjust_camera(
            start=tuple(camera["start"]),
            end=tuple(camera["end"]),
        )

        for troop in deploy["troops"]:
            slot = tuple(troop["slot"])
            if troop["type"] == "drag":
                actions.deploy_troop_drag(
                    troop_slot=slot,
                    drag_start=tuple(troop["drag_start"]),
                    drag_end=tuple(troop["drag_end"]),
                    duration=troop.get("duration", 1.5),
                )
            elif troop["type"] == "click":
                actions.deploy_troop_click(
                    troop_slot=slot,
                    target=tuple(troop["target"]),
                )

        for hero in deploy["heroes"]:
            actions.deploy_troop_click(
                troop_slot=tuple(hero["slot"]),
                target=tuple(hero["target"]),
            )

        actions.wait(timings["troop_engage_wait"])

        for spell in deploy["spells"]:
            actions.deploy_spell(
                spell_slot=tuple(spell["slot"]),
                target=tuple(spell["target"]),
                count=spell.get("count", 1),
            )

        actions.wait(timings["hero_ability_a          sdfactivate_after_deployment"])

        for ability_slot in deploy["hero_abilities"]:
            actions.activate_hero_ability(tuple(ability_slot))
        
        det = self.config.get("detection", {})
        ok, screen = self._wait_for(
                lambda s: tmpl.is_battle_over(s, self.templates),
                timeout=det["battle_over_timeout"],
                poll=det["poll_interval"],
        )
        if not ok: 
            logger.warning("Battle over screen not detected within {}s", det["battle_over_timeout"])
            self._dump_failure_screenshot(screen, reason="no_battle_end")
        self.transition(State.BATTLE_END)

    def _handle_attacking(self):
        """ATTACKING — battle in progress, wait for it to end."""
        pass

    def _handle_battle_end(self):
        """BATTLE_END → end battle → return home → IDLE."""
        actions.end_battle()
        actions.return_home()
        det = self.config.get("detection", {})
        ok, screen = self._wait_for(
            lambda s: tmpl.is_home_screen(s, self.templates),
            timeout=det["home_screen_timeout"],
            poll=det["poll_interval"],
        )

        if not ok: 
            logger.warning("Home screen not confirmed after battle")
            self._dump_failure_screenshot(screen, reason="home_time_out")
        self.transition(State.IDLE)

    def _handle_disconnected(self):
        """DISCONNECTED → wait and check again."""
        actions.wait(self.config["timings"]["reconnect_wait"])

    def _handle_reconnect(self):
        """RECONNECT_POPUP → click reconnect → wait → IDLE."""
        actions.click_reconnect()
        actions.wait(self.config["timings"]["reconnect_wait"])
        self.transition(State.IDLE)

    def _wait_for(self, predicate, timeout, poll=0.5):
        """Poll grab()+predicate until True or timeout. Returns (ok: bool, last_screen)."""
        deadline = time.time() + timeout
        screen = grab()
        while time.time() < deadline:
            screen = grab()
            if predicate(screen):
                return True, screen
            actions.wait(poll)
        return False, screen
