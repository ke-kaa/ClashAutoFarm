"""
Shared test fixtures / import shims.

The bot imports native, display-bound libraries (pyautogui, cv2, mss,
pytesseract) at module load. Unit tests exercise pure logic and should not
require a display or OpenCV, so we register lightweight stand-ins in
sys.modules before any bot/vision module is imported.
"""

import sys
import types
from unittest.mock import MagicMock


def _stub(name):
    if name not in sys.modules:
        sys.modules[name] = MagicMock(name=name)


for _mod in ["pyautogui", "cv2", "mss", "pytesseract", "pynput", "pynput.keyboard"]:
    _stub(_mod)


# numpy is real if installed; only stub if missing so array ops in tests still work.
try:
    import numpy  # noqa: F401
except ImportError:  # pragma: no cover
    sys.modules["numpy"] = MagicMock(name="numpy")
