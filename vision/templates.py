"""
vision/templates.py — Template matching for UI element detection.
"""

import cv2
from pathlib import Path


def load_template(template_dir="../assets/templates/"):
    """Load all PNG templates from a directory into a dict."""
    templates = {}
    for path in Path(template_dir).glob("*.png"):
        templates[path.stem] = cv2.imread(str(path))
    return templates


def find(screen, template, threshold=0.3):
    """Check if a template exists in the screen image. Both must be numpy arrays."""
    screen_edges = cv2.Canny(screen, 50, 150)
    template_edges = cv2.Canny(template, 50, 150)
    res = cv2.matchTemplate(screen_edges, template_edges, cv2.TM_CCOEFF_NORMED)

    _, max_val, _, _ = cv2.minMaxLoc(res)
    return max_val >= threshold


def is_disconnected(screen, templates):
    """Check if the wifi disconnected icon is visible."""
    return find(screen, template=templates["wifi_disconnected"])


def is_reconnect_popup(screen, templates):
    """Check if the reconnect popup is visible."""
    return find(screen, template=templates["reconnect_popup"])


def is_onscout_screen(screen, templates):
    """Check if the scout screen is visible."""
    return find(screen, templates["scout_screen"])
