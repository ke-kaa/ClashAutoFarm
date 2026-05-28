"""
vision/preprocess.py — Image preprocessing helpers for OCR and template matching.
"""

import cv2
import numpy as np


def to_grayscale(img):
    """Convert a BGR image to grayscale."""
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def upscale(img, factor=2):
    """Upscale an image by a factor using cubic interpolation."""
    width = int(img.shape[1] * factor)
    height = int(img.shape[0] * factor)
    return cv2.resize(img, (width, height), interpolation=cv2.INTER_CUBIC)


def threshold(img, val=180):
    """Binarize a grayscale image using a fixed threshold."""
    _, result = cv2.threshold(img, val, 255, cv2.THRESH_BINARY)
    return result


def threshold_otsu(img):
    """Binarize a grayscale image using Otsu's automatic thresholding."""
    _, result = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return result


def crop(img, region):
    """Crop a region from an image. Region is (x, y, w, h)."""
    x, y, w, h = region
    return img[y:y+h, x:x+w]


def invert(img):
    """Invert image colors (useful when digits are light on dark background)."""
    return cv2.bitwise_not(img)
