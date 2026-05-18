"""Rule-based image style scoring from OpenCV metrics."""

from __future__ import annotations

from typing import Dict, Mapping, Optional

import torch
from PIL import Image

STYLE_NAMES = ["luxury", "cozy", "vibrant", "minimal", "romantic", "adventurous"]


def _rule_based_scores(opencv_result: Optional[Mapping[str, float]]) -> Dict[str, float]:
    metrics = opencv_result or {}
    brightness = float(metrics.get("brightness", 0.5))
    saturation = float(metrics.get("saturation", 0.5))
    warm_tone = float(metrics.get("warm_tone", 0.5))
    contrast = float(metrics.get("contrast", 0.5))
    person_ratio = float(metrics.get("person_ratio", 0.0))

    return {
        "luxury": max(0.1, warm_tone * 0.5 + brightness * 0.3 + (1 - saturation) * 0.2),
        "cozy": max(0.1, warm_tone * 0.5 + brightness * 0.3 + (1 - contrast) * 0.2),
        "vibrant": max(0.1, saturation * 0.5 + brightness * 0.3 + person_ratio * 0.2),
        "minimal": max(0.1, (1 - saturation) * 0.5 + brightness * 0.3 + (1 - contrast) * 0.2),
        "romantic": max(0.1, warm_tone * 0.5 + saturation * 0.3 + (1 - contrast) * 0.2),
        "adventurous": max(0.1, contrast * 0.5 + saturation * 0.3 + (1 - warm_tone) * 0.2),
    }


def analyze_style(
    image: Image.Image,
    opencv_result: Optional[Mapping[str, float]] = None,
) -> Dict[str, float]:
    """Score style from OpenCV metrics only; returns softmax probabilities."""
    _ = image
    scores = _rule_based_scores(opencv_result)
    logits = torch.tensor([scores[name] for name in STYLE_NAMES], dtype=torch.float32)
    probs = torch.softmax(logits, dim=0)
    return {name: float(probs[i]) for i, name in enumerate(STYLE_NAMES)}
