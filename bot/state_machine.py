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
    def __init__(self, templates_dict, townhall_level=10, treasure_hunt=False):
        self.state = State.IDLE
        self.templates = templates_dict
        self.townhall_level = townhall_level
        self.config = load_config()
        self._state_entered_at = time.time()
        self.treasure_hunt = treasure_hunt
        self._attack_phase = None
        self._phase_deadline = 0

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
            if self.state != State.DISCONNECTED:
                self.transition(State.DISCONNECTED)
            self._handle_disconnected()
            return

        if tmpl.is_reconnect_popup(screen, self.templates):
            if self.state != State.RECONNECT_POPUP:
                self.transition(State.RECONNECT_POPUP)
            self._handle_reconnect()
            return

        # Network indicators cleared. If we were in a network state (with or without a
        # reconnect popup), confirm we're back at the home village before resuming.
        if self.state in (State.DISCONNECTED, State.RECONNECT_POPUP):
            self._handle_reconnected(screen)
            return

        if self.state == State.IDLE:
            self._handle_idle()
        elif self.state == State.FINDING_MATCH:
            self._handle_finding_match()
        elif self.state == State.SCOUTING:
            self._handle_scouting(screen)
        elif self.state == State.ATTACKING:
            self._handle_attacking(screen)
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
        ok, _ = self._wait_for(lambda s: not tmpl.is_onscout_screen(s, self.templates), timeout=det["scout_screen_timeout"], poll=det["poll_interval"])
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

        if meets_loot_threshold(self.townhall_level, loot, self.config):
            logger.info("Meets threshold — attacking")
            self._start_attack()
        else:
            logger.info("Below threshold — skipping")
            actions.click_next()
            actions.wait(self.config["timings"]["scout_wait"])

    def _start_attack(self):
        """Deploy troops and hand off to ATTACKING for tick-driven progression."""
        self.transition(State.ATTACKING)
        camera = self.config["camera"]

        actions.zoom_in()
        actions.adjust_camera(
            start=tuple(camera["start"]),
            end=tuple(camera["end"]),
        )
        self._deploy_troops()

        self._attack_phase = "engage_wait"
        self._phase_deadline = time.time() + self.config["timings"]["troop_engage_wait"]

    def _deploy_troops(self):
        """Fire the troop and hero deploy burst."""
        deploy = self.config["deploy"]
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

    def _deploy_spells(self):
        """Fire the spell deploy burst."""
        for spell in self.config["deploy"]["spells"]:
            actions.deploy_spell(
                spell_slot=tuple(spell["slot"]),
                target=tuple(spell["target"]),
                count=spell.get("count", 1),
            )

    def _activate_abilities(self):
        """Activate all hero abilities."""
        for ability_slot in self.config["deploy"]["hero_abilities"]:
            actions.activate_hero_ability(tuple(ability_slot))

    def _handle_attacking(self, screen):
        """ATTACKING — advance the deploy timeline, then poll for battle end."""
        timings = self.config["timings"]

        if self._attack_phase == "engage_wait":
            if time.time() < self._phase_deadline:
                return
            self._deploy_spells()
            self._attack_phase = "ability_wait"
            self._phase_deadline = time.time() + timings["hero_ability_activate_after_deployment"]

        elif self._attack_phase == "ability_wait":
            if time.time() < self._phase_deadline:
                return
            self._activate_abilities()
            self._attack_phase = "await_end"

        elif self._attack_phase == "await_end":
            if tmpl.is_battle_over(screen, self.templates):
                self.transition(State.BATTLE_END)

    def _handle_battle_end(self):
        """BATTLE_END → end battle → (claim reward | return home) → IDLE."""
        det = self.config.get("detection", {})
        if self.treasure_hunt:
            ok, screen = self._wait_for(
            lambda s: tmpl.is_claim_reward(s, self.templates) or tmpl.is_home_screen(s, self.templates),
            timeout=det["home_screen_timeout"], poll=det["poll_interval"],
            )
            if ok and tmpl.is_claim_reward(screen, self.templates):
                logger.info("Treasure Hunt chest earned — claiming reward")
                actions.claim_treasure_reward(self.config["treasure_hunt"])
                # claim sequence ends on the village home — no return_home() needed
            else:
                actions.return_home()
        else:
            actions.return_home()

        # Confirm we actually landed home (covers both the claim path and a normal return).
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
        """DISCONNECTED — network down, nothing to click. Wait and re-check next tick."""
        actions.wait(self.config["timings"]["reconnect_wait"])

    def _handle_reconnect(self):
        """RECONNECT_POPUP — dismiss the popup. Home is verified once indicators clear."""
        actions.click_reconnect()
        actions.wait(self.config["timings"]["reconnect_wait"])

    def _handle_reconnected(self, screen):
        """Network cleared — confirm the home village before resuming, else keep waiting."""
        if tmpl.is_home_screen(screen, self.templates):
            logger.info("Network recovered — home village confirmed")
            self.transition(State.IDLE)
        else:
            logger.warning("Network cleared but home village not confirmed — waiting")
            actions.wait(self.config["timings"]["reconnect_wait"])

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
