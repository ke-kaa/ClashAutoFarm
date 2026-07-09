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
    return match_score(screen, template) >= threshold


def is_disconnected(screen, templates, threshold=0.3):
    """Check if the wifi disconnected icon is visible."""
    return find(screen, template=templates["wifi_disconnected"], threshold=threshold)


def is_reconnect_popup(screen, templates, threshold=0.3):
    """Check if the reconnect popup is visible."""
    return find(screen, template=templates["reconnect_popup"], threshold=threshold)


def is_onscout_screen(screen, templates, threshold=0.3):
    """Check if the scout screen is visible."""
    return find(screen, templates["scout_screen"], threshold=threshold)


def is_home_screen(screen, templates, threshold=0.3):
    """Check if the home screen is visible."""
    return find(screen, templates["home_screen"], threshold=threshold)


def is_battle_over(screen, templates, threshold=0.3):
    """Check if the battle over screen is visible."""
    return find(screen, templates["battle_over"], threshold=threshold)


def is_claim_reward(screen, templates, threshold=0.3):
    """Check if the claim reward popup is visible."""
    return find(screen, templates["claim_reward"], threshold=threshold)


def match_score(screen, template):
    """Return the best template-match score (0..1) over the screen."""
    screen_edges = cv2.Canny(screen, 50, 150)
    template_edges = cv2.Canny(template, 50, 150)
    res = cv2.matchTemplate(screen_edges, template_edges, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    return max_val

