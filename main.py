"""
main.py — Entry point for the Clash Auto Farm bot.
"""

import argparse
import sys
import time
import threading
from pathlib import Path
from loguru import logger
from pynput import keyboard
from vision import templates
from bot.config_loader import load_and_validate, validate_treasure_hunt
from bot.state_machine import StateMachine

TEMPLATES_DIR = "/home/kaku/Documents/PersonalProjects/ClashAutoFarm/assets/templates/"
LOOP_TICK = 0.5
LOG_DIR = Path(__file__).resolve().parent / "logs"

_stop_event = threading.Event()


def _setup_logging():
    """Configure loguru: console + rotating file."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <level>{message}</level>",
        level="INFO",
    )
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        LOG_DIR / "bot.log",
        rotation="5 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}",
        level="DEBUG",
    )


def _on_key_press(key):
    """Stop the bot when ESC is pressed."""
    if key == keyboard.Key.esc:
        logger.warning("ESC pressed — stopping...")
        _stop_event.set()
        return False


def main():
    parser = argparse.ArgumentParser(description="Clash of Clans Auto Farm Bot")
    parser.add_argument("--townhall-level", type=int, default=10, choices=range(8, 19),
                        help="Your townhall level (8-18, default: 10)")
    parser.add_argument("--treasure-hunt", action="store_true", help="Enable treasure hunt claim handling at the end of battle")
    args = parser.parse_args()

    _setup_logging()
    logger.info("Loading config...")
    config = load_and_validate()

    templates_dict = templates.load_template(TEMPLATES_DIR)
    logger.info("Townhall level: {}", args.townhall_level)
    if args.treasure_hunt:
        logger.info("Treasure hunt claim handling: ENABLED")
        errs = validate_treasure_hunt(config)
        if errs: 
            for e in errs:
                logger.error(" . {}", e)
            sys.exit(1)

    machine = StateMachine(templates_dict, townhall_level=args.townhall_level, treasure_hunt=args.treasure_hunt,)

    listener = keyboard.Listener(on_press=_on_key_press)
    listener.start()

    logger.info("Switch to target window (5s)...")
    time.sleep(5)

    logger.info("Starting main loop (press ESC or Ctrl+C to stop)")
    try:
        while not _stop_event.is_set():
            machine.tick()
            time.sleep(LOOP_TICK)
    except KeyboardInterrupt:
        logger.warning("Stopped by Ctrl+C")
    finally:
        listener.stop()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
