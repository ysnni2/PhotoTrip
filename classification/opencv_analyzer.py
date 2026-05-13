"""Image color / tone metrics using OpenCV and NumPy."""

from __future__ import annotations

from typing import Any, Dict, List

import cv2
import numpy as np
from PIL import Image

_KMEANS_K = 5
_KMEANS_MAX_SIDE = 256
_KMEANS_CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.5)
_CONTRAST_STD_SCALE = 128.0  # max ~std for 0/255 split; map std to ~[0, 1]


def _pil_to_rgb_array(image: Image.Image) -> np.ndarray:
    if image.mode != "RGB":
        image = image.convert("RGB")
    return np.asarray(image, dtype=np.uint8)


def _resize_for_kmeans(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    m = max(h, w)
    if m <= _KMEANS_MAX_SIDE:
        return rgb
    scale = _KMEANS_MAX_SIDE / m
    return cv2.resize(
        rgb,
        (int(round(w * scale)), int(round(h * scale))),
        interpolation=cv2.INTER_AREA,
    )


def _dominant_color_kmeans(rgb: np.ndarray) -> List[int]:
    small = _resize_for_kmeans(rgb)
    pixels = small.reshape(-1, 3).astype(np.float32)
    if pixels.shape[0] < _KMEANS_K:
        k = max(1, pixels.shape[0])
    else:
        k = _KMEANS_K

    _, labels, centers = cv2.kmeans(
        pixels,
        k,
        None,
        _KMEANS_CRITERIA,
        10,
        cv2.KMEANS_PP_CENTERS,
    )
    labels = labels.ravel()
    counts = np.bincount(labels, minlength=k)
    dominant_idx = int(counts.argmax())
    rgb_vals = np.clip(np.round(centers[dominant_idx]), 0, 255).astype(int)
    return [int(rgb_vals[0]), int(rgb_vals[1]), int(rgb_vals[2])]


def analyze(image: Image.Image) -> Dict[str, Any]:
    """
    Analyze a PIL image: dominant RGB (K-means cluster with most pixels),
    brightness and saturation from HSV (0–1), contrast from grayscale std (0–1).
    """
    rgb = _pil_to_rgb_array(image)

    dominant = _dominant_color_kmeans(rgb)

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    brightness = float(hsv[:, :, 2].mean() / 255.0)
    saturation = float(hsv[:, :, 1].mean() / 255.0)

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    contrast = float(np.clip(gray.std() / _CONTRAST_STD_SCALE, 0.0, 1.0))

    return {
        "dominant_color": dominant,
        "brightness": brightness,
        "saturation": saturation,
        "contrast": contrast,
    }
