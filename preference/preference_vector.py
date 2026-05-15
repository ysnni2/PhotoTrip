"""Map CLIP / segmentation / OpenCV outputs to a scalar preference vector."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

import numpy as np


def _soft_or(*probs: float) -> float:
    """Combine independent-ish evidence in [0, 1] (1 - ∏(1 - p)))."""
    p = 1.0
    for x in probs:
        x = float(np.clip(x, 0.0, 1.0))
        p *= 1.0 - x
    return float(np.clip(1.0 - p, 0.0, 1.0))


def _mean(*vals: float) -> float:
    xs = [float(np.clip(v, 0.0, 1.0)) for v in vals]
    return float(sum(xs) / len(xs)) if xs else 0.0


def _warm_tone_from_rgb(rgb: List[int]) -> float:
    """Higher when R dominates over B (warm / sunset / sand), lower for cool tones."""
    r, g, b = (max(0, int(c)) for c in rgb[:3])
    denom = r + g + b + 1e-6
    # (R - B) / sum in ~[-1, 1]; map to [0, 1] with neutral gray ≈ 0.5
    return float(np.clip((r - b) / denom / 2.0 + 0.5, 0.0, 1.0))


def generate(
    clip_result: Mapping[str, float],
    seg_result: Mapping[str, float],
    cv_result: Mapping[str, Any],
) -> Dict[str, float]:
    """
    Build a preference vector from CLIP scene probs, ADE segment ratios, and CV metrics.

    - beach / nature / city / indoor / culture / fashion / food: primary theme scores for recommend()
    - beach_affinity, nature_affinity, urban_affinity, …: legacy / detailed signals
    """
    beach = float(clip_result.get("Beach", 0.0))
    nature = float(clip_result.get("Nature", 0.0))
    city = float(clip_result.get("City", 0.0))
    indoor = float(clip_result.get("Indoor", 0.0))

    water = float(seg_result.get("water", 0.0))
    sand = float(seg_result.get("sand", 0.0))
    vegetation = float(seg_result.get("vegetation", 0.0))
    building = float(seg_result.get("building", 0.0))
    road = float(seg_result.get("road", 0.0))

    beach_affinity = _soft_or(beach, water, sand)
    nature_affinity = _soft_or(nature, vegetation)
    urban_affinity = _mean(city, building, road)

    indoor_restaurant_affinity = float(np.clip(indoor * 0.6, 0.0, 1.0))
    indoor_museum_affinity = float(np.clip(indoor * 0.4, 0.0, 1.0))

    dom = cv_result.get("dominant_color", [128, 128, 128])
    if not isinstance(dom, (list, tuple)) or len(dom) < 3:
        dom = [128, 128, 128]
    warm_tone = _warm_tone_from_rgb(list(dom))

    brightness = float(np.clip(cv_result.get("brightness", 0.0), 0.0, 1.0))
    saturation = float(np.clip(cv_result.get("saturation", 0.0), 0.0, 1.0))

    night_preference = float(np.clip(1.0 - brightness, 0.0, 1.0))

    indoor_strength = float(
        np.clip(indoor_restaurant_affinity + indoor_museum_affinity, 0.0, 1.0)
    )
    culture_clip = float(np.clip(clip_result.get("Culture", 0.0), 0.0, 1.0))
    fashion_clip = float(np.clip(clip_result.get("Fashion", 0.0), 0.0, 1.0))
    food_clip = float(np.clip(clip_result.get("Food", 0.0), 0.0, 1.0))

    return {
        "beach": beach_affinity,
        "nature": nature_affinity,
        "city": urban_affinity,
        "indoor": indoor_strength,
        "culture": culture_clip,
        "fashion": fashion_clip,
        "food": food_clip,
        "beach_affinity": beach_affinity,
        "nature_affinity": nature_affinity,
        "urban_affinity": urban_affinity,
        "indoor_restaurant_affinity": indoor_restaurant_affinity,
        "indoor_museum_affinity": indoor_museum_affinity,
        "warm_tone": warm_tone,
        "brightness": brightness,
        "saturation": saturation,
        "night_preference": night_preference,
    }
