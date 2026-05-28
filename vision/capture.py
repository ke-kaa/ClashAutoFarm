"""
vision/capture.py — Fast screen capture using mss.
"""

import mss
import numpy as np
import cv2

_sct = mss.mss()


def grab(region=None):
    """Capture a screen region and return it as a BGR numpy array."""
    monitor = region or _sct.monitors[1]
    sct_img = _sct.grab(monitor)
    frame = np.array(sct_img)
    return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)


def save_screenshot(img, path):
    """Save a numpy image to disk for debugging."""
    cv2.imwrite(path, img)
