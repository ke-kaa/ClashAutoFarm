"""
Debug harness for vision.ocr.locate_text.

Prints every step so you can see where account-name detection fails.

Usage (from the repo root):
    .venv/bin/python -m calibration.debug_locate_text                # live: grab() the screen
    .venv/bin/python -m calibration.debug_locate_text some_shot.png  # test against a saved image

Edit CARD_REGION and TARGETS below to match your setup.
CARD_REGION is [x, y, w, h]  (top-left x, top-left y, width, height) — NOT two corners.
"""

import sys
import cv2
import pytesseract
from pytesseract import Output

from vision.preprocess import crop, to_grayscale, upscale

# ---- edit these -------------------------------------------------------------
CARD_REGION = [600, 100, 680, 620]   # [x, y, w, h] around the account list
TARGETS = ["GuardianDeity0", "GuardianDeityI", "GuardianDeityII", "GuardianDeityIII"]
UPSCALE = 3
# -----------------------------------------------------------------------------


def _normalize(text):
    return "".join(text.split()).lower()


def main():
    # 1. load the screen (saved image if a path is given, else live grab)
    if len(sys.argv) > 1:
        path = sys.argv[1]
        screen = cv2.imread(path)
        print(f"[1] loaded image: {path}")
        if screen is None:
            print("    ERROR: could not read image (bad path?)")
            return
    else:
        from vision.capture import grab
        screen = grab()
        print("[1] grabbed live screen")
    print(f"    screen shape (h, w, c): {screen.shape}")

    # 2. show the region and sanity-check it fits inside the screen
    x, y, w, h = CARD_REGION
    sh, sw = screen.shape[:2]
    print(f"[2] CARD_REGION [x={x}, y={y}, w={w}, h={h}]")
    if w <= 0 or h <= 0:
        print("    ERROR: width/height must be > 0. Did you pass [x1,y1,x2,y2] instead of [x,y,w,h]?")
        return
    if x + w > sw or y + h > sh or x < 0 or y < 0:
        print(f"    WARNING: region extends outside the screen ({sw}x{sh}) — crop will be clipped/empty")

    # 3. crop and save it so you can eyeball what OCR sees
    cropped = crop(screen, CARD_REGION)
    print(f"[3] cropped shape (h, w, c): {cropped.shape}")
    if cropped.size == 0:
        print("    ERROR: crop is EMPTY — the region is wrong. Fix CARD_REGION.")
        return
    cv2.imwrite("debug_crop.png", cropped)
    print("    saved debug_crop.png  (open it: does it show the account names?)")

    # 4. preprocess exactly like locate_text
    scaled = upscale(to_grayscale(cropped), factor=UPSCALE)
    cv2.imwrite("debug_scaled.png", scaled)
    print(f"[4] preprocessed (gray + {UPSCALE}x upscale) shape: {scaled.shape}")
    print("    saved debug_scaled.png")

    # 5. raw OCR dump — every token, its confidence, and box
    try:
        data = pytesseract.image_to_data(scaled, config="--psm 6", output_type=Output.DICT)
    except Exception as e:
        print(f"    ERROR calling tesseract: {e}")
        print("    (is the tesseract binary installed and on PATH?)")
        return
    print("[5] raw OCR tokens (text | conf | left,top,w,h):")
    any_token = False
    for i in range(len(data["text"])):
        t = data["text"][i].strip()
        if not t:
            continue
        any_token = True
        print(f"      {t!r:24} conf={data['conf'][i]:>4}  "
              f"{data['left'][i]},{data['top'][i]},{data['width'][i]},{data['height'][i]}")
    if not any_token:
        print("      (nothing recognized — wrong region, or OCR can't read this image)")

    # 6. reconstruct lines (same grouping locate_text uses)
    lines = {}
    for i in range(len(data["text"])):
        word = data["text"][i].strip()
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = -1
        if not word or conf < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        left, top = data["left"][i], data["top"][i]
        right, bottom = left + data["width"][i], top + data["height"][i]
        ln = lines.setdefault(key, {"words": [], "l": left, "t": top, "r": right, "b": bottom})
        ln["words"].append(word)
        ln["l"], ln["t"] = min(ln["l"], left), min(ln["t"], top)
        ln["r"], ln["b"] = max(ln["r"], right), max(ln["b"], bottom)
    print("[6] reconstructed lines (normalized):")
    for ln in lines.values():
        print(f"      {_normalize(''.join(ln['words']))!r}")

    # 7. match each target against the lines and show the computed click point
    print("[7] matching targets:")
    for target in TARGETS:
        wanted = _normalize(target)
        hit = None
        for ln in lines.values():
            if _normalize("".join(ln["words"])) == wanted:
                cx = (ln["l"] + ln["r"]) / 2 / UPSCALE + x
                cy = (ln["t"] + ln["b"]) / 2 / UPSCALE + y
                hit = (int(cx), int(cy))
                break
        print(f"      {target:22} normalized={wanted!r:22} -> {hit}")


if __name__ == "__main__":
    main()
