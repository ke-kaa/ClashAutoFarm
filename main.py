"""
main.py — Entry point for the Clash Auto Farm bot.
"""

import argparse
import os
import sys
import time
import threading
from pathlib import Path
import re
from datetime import timedelta
from datetime import datetime

from loguru import logger
from pynput import keyboard

from vision import templates
from bot.config_loader import load_and_validate, validate_treasure_hunt, validate_max_loot
from bot import state_machine
from bot.state_machine import StateMachine
from bot.dry_run import DryRunActions
from utils.csv_writer import setup_csv_writer
from utils.notifier import NullNotifier, TelegramNotifier

TEMPLATES_DIR = Path(__file__).resolve().parent / "assets" / "templates"
LOOP_TICK = 0.5
LOG_DIR = Path(__file__).resolve().parent / "logs"
_DURATION_RE = re.compile(r"(\d+)(s|min|m|h|d)")

stop_event = threading.Event()


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
        stop_event.set()
        return False


def _build_notifier(enabled):
    if not enabled:
        return NullNotifier()
    token = os.getenv("COC_TELEGRAM_TOKEN")
    chat_id = os.getenv("COC_TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        logger.warning(
            "--notify set but COC_TELEGRAM_TOKEN/COC_TELEGRAM_CHAT_ID missing; disabled"
        )
        return NullNotifier()
    logger.info("Telegram notifications: ENABLED")
    return TelegramNotifier(token, chat_id)


def parse_duration(value: str) -> timedelta:
    pos = 0
    total = timedelta()

    for match in _DURATION_RE.finditer(value.lower()):
        if match.start() != pos:
            raise argparse.ArgumentTypeError(
                f"Invalid duration: {value}, Examples: 30s, 5m, 30min, 2h, 1d, 2h30min"
            )

        amount = int(match.group(1))
        unit = match.group(2)

        if unit == "d":
            total += timedelta(days=amount)
        elif unit == "h":
            total += timedelta(hours=amount)
        elif unit in ("m", "min"):
            total += timedelta(minutes=amount)
        elif unit == "s":
            total += timedelta(seconds=amount)

        pos = match.end()

    if pos != len(value):
        raise argparse.ArgumentTypeError(f"Invalid duration: {value}")

    return total


def main():
    parser = argparse.ArgumentParser(description="Clash of Clans Auto Farm Bot")
    parser.add_argument(
        "--townhall-level",
        type=int,
        default=10,
        choices=range(8, 19),
        help="Your townhall level (8-18, default: 10)",
    )
    parser.add_argument(
        "--treasure-hunt",
        action="store_true",
        help="Enable treasure hunt claim handling at the end of battle",
    )
    parser.add_argument("--account-name", help="current account's name for csv logging")
    parser.add_argument(
        "--max-attacks",
        type=int,
        default=0,
        help="Maximum number of attacks before stopping (0 for unlimited)",
    )
    parser.add_argument(
        "--max-runtime",
        type=parse_duration,
        default=0,
        help="Maximum run time (e.g. 30s, 5m, 30min, 2h, 0 for unlimited)",
    )
    parser.add_argument(
        "--max-loot",
        action="store_true",
        help="Stop when loot is maxed out",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run detection and decisions but perform no clicks",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Send Telegram notifications (needs COC_TELEGRAM_TOKEN/CHAT_ID)",
    )

    args = parser.parse_args()

    _setup_logging()
    logger.info("Loading config...")
    config = load_and_validate()
    csv_writer = setup_csv_writer()

    if args.dry_run:
        logger.warning("DRY-RUN: no clicks will be performed")
        state_machine.actions = DryRunActions()

    templates_dict = templates.load_template(TEMPLATES_DIR)
    logger.info("Townhall level: {}", args.townhall_level)
    if args.treasure_hunt:
        logger.info("Treasure hunt claim handling: ENABLED")
        errs = validate_treasure_hunt(config)
        if errs:
            for e in errs:
                logger.error(" . {}", e)
            sys.exit(1)

    if args.max_loot:
        errs = validate_max_loot(config)
        if errs:
            for e in errs:
                logger.error(" . {}", e)
            sys.exit(1)

    notifier = _build_notifier(args.notify)

    machine = StateMachine(
        templates_dict,
        townhall_level=args.townhall_level,
        treasure_hunt=args.treasure_hunt,
        csv_writer=csv_writer,
        stop_event=stop_event,
        args=args,
        start_time=datetime.now(),
        notifier=notifier,
    )

    listener = keyboard.Listener(on_press=_on_key_press)
    listener.start()

    logger.info("Switch to target window (5s)...")
    time.sleep(5)

    start_time = time.strftime("%Y-%m-%d %H:%M:%S")
    heartbeat_interval = config.get("notify", {}).get("heartbeat_interval", 0)
    next_heartbeat = time.monotonic() + heartbeat_interval if heartbeat_interval else None
    logger.info("Starting main loop (press ESC or Ctrl+C to stop)")
    try:
        while not stop_event.is_set():
            machine.tick()
            if next_heartbeat and time.monotonic() >= next_heartbeat:
                notifier.send(
                    f"alive | attacks={machine.total_attacked} "
                    f"skips={machine.total_skipped}"
                )
                next_heartbeat = time.monotonic() + heartbeat_interval
            time.sleep(LOOP_TICK)
    except KeyboardInterrupt:
        logger.warning("Stopped by Ctrl+C")
    finally:
        row = {
            "start_time": start_time,
            "stop_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "account_name": args.account_name,
            "townhall_level": args.townhall_level,
            "total_attacked": machine.total_attacked,
            "total_skipped": machine.total_skipped,
            "total_gold": machine.total_loot.get("gold"),
            "total_elixir": machine.total_loot.get("elixir"),
            "total_dark_elixir": machine.total_loot.get("dark_elixir"),
        }
        csv_writer.write("account_summary", row)
        csv_writer.close()
        notifier.send(
            f"session ended | attacks={machine.total_attacked} "
            f"skips={machine.total_skipped} gold={machine.total_loot.get('gold')} "
            f"elixir={machine.total_loot.get('elixir')} dark={machine.total_loot.get('dark_elixir')}"
        )
        listener.stop()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
