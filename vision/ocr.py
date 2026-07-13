"""
vision/ocr.py — Loot extraction via Tesseract OCR.
"""

import pytesseract
import re
from vision.preprocess import to_grayscale, upscale, threshold, crop, invert


TESSERACT_CONFIG_SINGLE = "--psm 7 -c tessedit_char_whitelist=0123456789"
TESSERACT_CONFIG_BLOCK = "--psm 6 -c tessedit_char_whitelist=0123456789"


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
    text = pytesseract.image_to_string(binary, config=TESSERACT_CONFIG_SINGLE)
    return _parse_number(text)


def read_loot(screen, regions, battle_end=False):
    """
    Read gold, elixir, and dark elixir from a single loot region.

    Tesseract reads all three numbers at once from one crop.
    The result is split by newlines — line 0 = gold, 1 = elixir, 2 = dark.

    Parameters
    ----------
    screen  : numpy array (BGR) — full screenshot from grab()
    regions : dict with key 'loot_region' mapping to an (x, y, w, h) list

    Returns
    -------
    dict with keys 'gold', 'elixir', 'dark_elixir', values are ints (-1 on failure)
    """
    loot_region = regions.get("loot_region") if not battle_end else regions.get("loot_region_battle_end")
    if not loot_region:
        return {"gold": -1, "elixir": -1, "dark_elixir": -1}

    cropped = crop(screen, loot_region)
    gray = to_grayscale(cropped)
    scaled = upscale(gray, factor=3)
    binary = threshold(scaled, val=180)
    text = pytesseract.image_to_string(binary, config=TESSERACT_CONFIG_BLOCK)

    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    keys = ["gold", "elixir", "dark_elixir"]

    result = {}
    for i, key in enumerate(keys):
        if i < len(lines):
            result[key] = _parse_number(lines[i])
        else:
            result[key] = -1

    return result

