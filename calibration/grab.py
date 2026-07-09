"""
python calibration/grab.py scrout_screen match (for a matching screen)
python calibration/grab.py scrout_screen mismatch (for a non-matching screen)
"""

import sys, time
from vision.capture import save_screenshot, grab

key, bucket = sys.argv[1], sys.argv[2]
save_screenshot(grab(), f"../assets/templates/{bucket}/{key}/{int(time.time())}.png")
