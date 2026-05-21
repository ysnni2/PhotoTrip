"""Visual tone metrics from a PIL image using OpenCV and NumPy."""

from __future__ import annotations

from typing import Any, Dict, Optional

import cv2
import numpy as np
from PIL import Image

_CONTRAST_STD_SCALE = 128.0
_face_cascade: Optional[cv2.CascadeClassifier] = None


def _get_face_cascade() -> cv2.CascadeClassifier:
    global _face_cascade
    if _face_cascade is None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _face_cascade = cv2.CascadeClassifier(cascade_path)
    return _face_cascade


def _person_ratio_from_faces(rgb: np.ndarray) -> float:
    """Face bounding-box area sum / image pixels (proxy for person presence)."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    faces = _get_face_cascade().detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(24, 24),
    )
    h, w = gray.shape[:2]
    total = h * w
    if total == 0:
        return 0.0
    face_area = sum(int(fw) * int(fh) for _x, _y, fw, fh in faces)
    return float(np.clip(face_area / total, 0.0, 1.0))


_cat_cascade: Optional[cv2.CascadeClassifier] = None


def _get_cat_cascade() -> cv2.CascadeClassifier:
    global _cat_cascade
    if _cat_cascade is None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalcatface.xml"
        _cat_cascade = cv2.CascadeClassifier(cascade_path)
    return _cat_cascade


def _cat_detection(rgb: np.ndarray) -> tuple[bool, float]:
    """Frontal cat-face Haar detection → (detected flag, bbox area ratio)."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    cats = _get_cat_cascade().detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(24, 24),
    )
    h, w = gray.shape[:2]
    total = h * w
    if total == 0:
        return False, 0.0
    cat_detected = len(cats) > 0
    cat_area = sum(int(cw) * int(ch) for _x, _y, cw, ch in cats)
    animal_ratio = float(np.clip(cat_area / total, 0.0, 1.0))
    return cat_detected, animal_ratio


def _pil_to_rgb_array(image: Image.Image) -> np.ndarray:
    if image.mode != "RGB":
        image = image.convert("RGB")
    return np.asarray(image, dtype=np.uint8)


def analyze(image: Image.Image) -> Dict[str, Any]:
    """
    Extract brightness, saturation, contrast, warm_tone, and person_ratio (all in [0, 1]).

    person_ratio: detected frontal-face area / total pixels (Haar cascade).
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

    saturated = hsv[:, :, 1] >= 40
    total_sat = int(saturated.sum())
    if total_sat > 0:
        h = hsv[:, :, 0]
        blue_tone = float(((saturated) & (h >= 90) & (h <= 140)).sum() / total_sat)
        green_tone = float(((saturated) & (h >= 35) & (h <= 85)).sum() / total_sat)
    else:
        blue_tone = green_tone = 0.0
    night_score = float(np.clip((1.0 - brightness) * contrast, 0.0, 1.0))

    person_ratio = _person_ratio_from_faces(rgb)
    cat_detected, animal_ratio = _cat_detection(rgb)

    return {
        "brightness": brightness,
        "saturation": saturation,
        "contrast": contrast,
        "warm_tone": warm_tone,
        "blue_tone": float(np.clip(blue_tone, 0.0, 1.0)),
        "green_tone": float(np.clip(green_tone, 0.0, 1.0)),
        "night_score": night_score,
        "person_ratio": person_ratio,
        "cat_detected": cat_detected,
        "animal_ratio": animal_ratio,
    }
