"""
test_ocr.py — Test OCR loot reading on the scouting screen.

Usage:
  1. Open Clash of Clans and go to a scouting screen (enemy base with loot visible)
  2. Run this script
  3. You have 5 seconds to switch to the game window
  4. Check the output + saved images
"""

import time
import cv2
from vision.capture import grab, save_screenshot
from vision.preprocess import to_grayscale, upscale, threshold, crop
from vision.ocr import read_loot
from bot.config_loader import load_config

config = load_config()
regions = config.get("regions", {})
loot_region = regions.get("loot_region")

print(f"Loot region from config: {loot_region}")
if not loot_region:
    print("ERROR: loot_region is not set in config.yaml")
    exit()

print("Switch to the scouting screen... (5 seconds)")
time.sleep(5)

# Capture full screen
screen = grab()
save_screenshot(screen, "test_full_screen.png")
print("Saved: test_full_screen.png")

# Crop the loot region
cropped = crop(screen, loot_region)
cv2.imwrite("test_loot_crop.png", cropped)
print("Saved: test_loot_crop.png  (check this shows the 3 loot numbers)")

# Show preprocessing steps
gray = to_grayscale(cropped)
cv2.imwrite("test_loot_gray.png", gray)

scaled = upscale(gray, factor=3)
cv2.imwrite("test_loot_scaled.png", scaled)

binary = threshold(scaled, val=180)
cv2.imwrite("test_loot_binary.png", binary)
print("Saved: test_loot_gray.png, test_loot_scaled.png, test_loot_binary.png")

# Run OCR
loot = read_loot(screen, regions)
print()
print("=== OCR Results ===")
print(f"  Gold:         {loot['gold']}")
print(f"  Elixir:       {loot['elixir']}")
print(f"  Dark Elixir:  {loot['dark_elixir']}")
print()
print("Compare these to what you see on screen.")
print("If wrong, check test_loot_crop.png and test_loot_binary.png")
