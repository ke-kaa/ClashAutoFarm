"""
bot/dry_run.py — No-op stand-in for bot.actions used by --dry-run.

Logs every mutating call instead of performing it; keeps `wait` real so the
tick-driven timeline still advances at wall-clock pace.
"""

from loguru import logger

from bot import actions as _real


class DryRunActions:
    def click_attack_button(self, *a, **k):
        logger.info("[dry-run] click_attack_button")

    def click_find_match(self, *a, **k):
        logger.info("[dry-run] click_find_match")

    def use_army_recipe(self, *a, **k):
        logger.info("[dry-run] use_army_recipe")

    def click_confirm_attack(self, *a, **k):
        logger.info("[dry-run] click_confirm_attack")

    def click_next(self, *a, **k):
        logger.info("[dry-run] click_next")

    def click_reconnect(self, *a, **k):
        logger.info("[dry-run] click_reconnect")

    def zoom_in(self, *a, **k):
        logger.info("[dry-run] zoom_in")

    def adjust_camera(self, *a, **k):
        logger.info("[dry-run] adjust_camera {} {}", a, k)

    def deploy_troop_drag(self, *a, **k):
        logger.info("[dry-run] deploy_troop_drag {} {}", a, k)

    def deploy_troop_click(self, *a, **k):
        logger.info("[dry-run] deploy_troop_click {} {}", a, k)

    def deploy_spell(self, *a, **k):
        logger.info("[dry-run] deploy_spell {} {}", a, k)

    def activate_hero_ability(self, *a, **k):
        logger.info("[dry-run] activate_hero_ability {}", a)

    def return_home(self, *a, **k):
        logger.info("[dry-run] return_home")

    def claim_treasure_reward(self, *a, **k):
        logger.info("[dry-run] claim_treasure_reward")

    def wait(self, seconds):
        _real.wait(seconds)
