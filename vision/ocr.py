"""
vision/ocr.py — Loot extraction via Tesseract OCR.
"""

import pytesseract
import re
from vision.preprocess import to_grayscale, upscale, threshold, crop, invert


TESSERACT_CONFIG = "--psm 7 -c tessedit_char_whitelist=0123456789"


def _parse_number(text):
    """Extract an integer from OCR text. Returns -1 on failure."""
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        return -1
    return int(digits)


def read_number(img):
    """
    Run the preprocessing pipeline on a single loot region and return an int.

    Pipeline: grayscale → upscale 3x → threshold → Tesseract (digits only).
    Pass in a BGR numpy array cropped to the loot region.
    Returns -1 on parse failure so the caller can retry.
    """
    gray = to_grayscale(img)
    scaled = upscale(gray, factor=3)
    binary = threshold(scaled, val=180)
    text = pytesseract.image_to_string(binary, config=TESSERACT_CONFIG)
    return _parse_number(text)


def read_loot(screen, regions):
    """
    Read gold, elixir, and dark elixir from a full screenshot.

    Parameters
    ----------
    screen  : numpy array (BGR) — full screenshot from grab()
    regions : dict with keys 'gold_loot', 'elixir_loot', 'dark_loot',
              each mapping to an (x, y, w, h) tuple

    Returns
    -------
    dict with keys 'gold', 'elixir', 'dark_elixir', values are ints (-1 on failure)
    """
    result = {}
    for key, name in [("gold", "gold_loot"), ("elixir", "elixir_loot"), ("dark_elixir", "dark_loot")]:
        region = regions.get(name)
        if region:
            cropped = crop(screen, region)
            result[key] = read_number(cropped)
        else:
            result[key] = -1
    return result
