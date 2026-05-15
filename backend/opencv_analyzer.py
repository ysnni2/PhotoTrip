"""Visual tone metrics from a PIL image using OpenCV and NumPy."""

from __future__ import annotations

from typing import Dict

import cv2
import numpy as np
from PIL import Image

_CONTRAST_STD_SCALE = 128.0


def _pil_to_rgb_array(image: Image.Image) -> np.ndarray:
    if image.mode != "RGB":
        image = image.convert("RGB")
    return np.asarray(image, dtype=np.uint8)


def analyze(image: Image.Image) -> Dict[str, float]:
    """
    Extract brightness, saturation, contrast, and warm_tone (all in [0, 1]).

    warm_tone: mean of per-pixel (R - B) / (R + G + B), mapped to [0, 1].
    """
    rgb = _pil_to_rgb_array(image)

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    brightness = float(np.clip(hsv[:, :, 2].mean() / 255.0, 0.0, 1.0))
    saturation = float(np.clip(hsv[:, :, 1].mean() / 255.0, 0.0, 1.0))

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    contrast = float(np.clip(gray.std() / _CONTRAST_STD_SCALE, 0.0, 1.0))

    r = rgb[:, :, 0].astype(np.float32)
    g = rgb[:, :, 1].astype(np.float32)
    b = rgb[:, :, 2].astype(np.float32)
    warm = (r - b) / (r + g + b + 1e-6) / 2.0 + 0.5
    warm_tone = float(np.clip(warm.mean(), 0.0, 1.0))

    return {
        "brightness": brightness,
        "saturation": saturation,
        "contrast": contrast,
        "warm_tone": warm_tone,
    }
