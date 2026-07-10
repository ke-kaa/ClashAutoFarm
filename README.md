# ClashAutoFarm

A vision-driven automation bot for farming in Clash of Clans. It watches the screen, decides whether a
scouted base is worth attacking, deploys a configured army, and loops — all without game-API access,
using screen capture, template matching, and OCR.

> ⚠️ **Disclaimer.** Automating Clash of Clans violates Supercell's Terms of Service and can result in
> a ban. This project is for educational and personal experimentation only. Use at your own risk.

---

## How it works

The bot runs a tick loop (`main.py`) that drives a state machine. Each tick captures the screen, runs
safety checks, and advances the current state:

```
IDLE ──▶ FINDING_MATCH ──▶ SCOUTING ──▶ ATTACKING ──▶ BATTLE_END ──▶ IDLE
                                │  (loot below threshold → skip → next base)
                                ▼
                          read loot (OCR)

  any state ──▶ DISCONNECTED / RECONNECT_POPUP  (checked every tick)
```

- **`vision/`** — perception. `capture.py` (fast screen grab via `mss`), `templates.py` (UI detection
  via OpenCV template matching), `ocr.py` + `preprocess.py` (loot reading via Tesseract).
- **`bot/`** — control. `state_machine.py` (states + transitions), `actions.py` (click/drag wrappers
  over `pyautogui`), `config_loader.py` (load + validate `config.yaml`).
- **`config.yaml`** — all coordinates, timings, loot thresholds, and detection tuning live here, so
  behavior is data-driven rather than hardcoded.

The attack loop is **tick-driven**: deploys fire as a burst, then the waits and the battle-over check
are polled one step per tick, so `ESC`, stuck-state timeouts, and disconnect detection stay live
throughout a battle.

---

## Features

- Automatic attack cycle: search → scout → evaluate loot → deploy army → return home → repeat.
- **Loot-threshold filtering** per Town Hall level (skips low-value bases).
- **Vision-confirmed transitions** (waits for the real screen instead of blind delays).
- **Disconnect / reconnect handling.**
- **Treasure Hunt event support** (`--treasure-hunt`): claims the end-of-battle chest when present.
- **Stuck-state recovery**: per-state timeouts dump a screenshot to `logs/failures/` and reset.
- `ESC` to stop cleanly.

---

## Requirements

- **Python 3.12+**
- **Tesseract OCR binary** on `PATH` (`pytesseract` needs it; it is *not* a pip package):
  - Linux: `sudo apt install tesseract-ocr`
  - Windows: install from the [UB-Mannheim build](https://github.com/UB-Mannheim/tesseract/wiki)
- **A real display.** `pyautogui` (clicking), `pynput` (ESC listener), and `mss` (capture) all require
  an active desktop session — this cannot run truly headless. On Linux, full `opencv-python` also needs
  system libs (`libGL.so.1`, `libglib2.0`).

See `WINDOWS_SETUP_GUIDE.md` for detailed Windows setup.

---

## Installation

### Option A — uv (recommended)

```bash
git clone <repo-url>
cd ClashAutoFarm
uv sync            # creates .venv and installs dependencies from the lockfile
```

### Option B — pip + venv

```bash
git clone <repo-url>
cd ClashAutoFarm
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install .                      # installs the project + its declared dependencies
pip install pytest                 # optional: test tooling (dev dependency group)
```

Verify the vision stack imports (OpenCV in particular — see Troubleshooting):

```bash
# uv:
uv run python -c "import cv2, pyautogui, pytesseract; print('ok', cv2.__version__)"
# pip/venv (with the venv activated):
python -c "import cv2, pyautogui, pytesseract; print('ok', cv2.__version__)"
```

---

## Configuration

Everything lives in `config.yaml`:

| Section | Purpose |
|---|---|
| `timings` | Fixed waits (match wait, deploy waits, result-screen wait, …) |
| `regions` | Screen regions for OCR (`loot_region`, …) |
| `camera` | Zoom/pan drag coordinates before deploying |
| `deploy` | Troop / hero / spell / ability slots and deploy targets |
| `thresholds` | Minimum loot per Town Hall level (gold+elixir total, dark elixir) |
| `detection` | Confirmation timeouts + poll interval for vision-confirmed transitions |
| `treasure_hunt` | Claim-sequence coordinates (used with `--treasure-hunt`) |

**Coordinates are resolution- and layout-specific.** You must capture your own for your screen. The
template-matching thresholds also need calibration — the default `0.3` is deliberately loose and will
false-positive; see the calibration workflow in `docs/` before relying on the vision checks.

Config is validated on startup; invalid values abort with a clear message.

---

## Usage

```bash
# Basic run for a Town Hall 12 account
uv run main.py --townhall-level 12

# Enable Treasure Hunt chest claiming
uv run main.py --townhall-level 12 --treasure-hunt
```

| Flag | Description |
|---|---|
| `--townhall-level {8..18}` | Your TH level; selects the loot threshold row (default: 10) |
| `--treasure-hunt` | Claim the end-of-battle chest when the event is active |

After launch you get 5 seconds to switch to the game window. Press **`ESC`** (or `Ctrl+C`) to stop.
Logs stream to the console and to `logs/bot.log`; failure screenshots land in `logs/failures/`.

---

## Testing

Headless unit tests (native/display deps are stubbed, so no game or display required):

```bash
uv run pytest
```

Covers config validation, the state-machine transitions and tick-driven attack timeline, the
treasure-hunt click sequence, and template-predicate wiring. `tests/manual_ocr_check.py` is a
live-capture script (run manually against the game), not part of the automated suite.

---

## Project structure

```
main.py                 entry point + tick loop
config.yaml             all tunables (coords, timings, thresholds)
bot/
  state_machine.py      states, transitions, attack timeline
  actions.py            click/drag wrappers (pyautogui)
  config_loader.py      load + validate config
vision/
  capture.py            screen grab (mss)
  templates.py          UI detection (OpenCV template match)
  ocr.py, preprocess.py loot reading (Tesseract)
assets/templates/       reference images for matching
tests/                  pytest suite
logs/                   runtime logs + failure screenshots
```

---

## Troubleshooting

- **`AttributeError: module 'cv2' has no attribute '__version__'` / `cv2` has no `imread`** — OpenCV is
  installed broken (empty `cv2` package). This also breaks `pyautogui` (it reads `cv2.__version__` at
  import). Fix: `uv pip install --reinstall opencv-python` (or `uv sync`).
- **`TesseractNotFoundError`** — the Tesseract *binary* isn't on `PATH`. Install it (see Requirements).
- **Vision checks always trigger / never trigger** — template thresholds aren't calibrated. The default
  `0.3` is too loose; calibrate per-template (see `docs/`).
- **Clicks land in the wrong place** — coordinates in `config.yaml` don't match your resolution/layout.
  Recapture them.

---

## Future improvements

A full, prioritized backlog — effectiveness, operability, farming-cycle expansion (storage-full
detection, account switching, wall upgrades), and an ML/AI perception layer (YOLO object detection +
optional VLM menu navigation) — is planned.

Highlights:
- **Effectiveness:** army-ready check before searching, army strategy profiles.
- **Operability:** session stats / loot ledger, stop conditions, remote notifications, dry-run mode,
  pause/resume.
- **Farming cycle:** stop/switch when storages are full, multi-account rotation, auto wall upgrades.
- **AI/ML:** replace hand-tuned coordinates + template matching with a trained object detector.
```
