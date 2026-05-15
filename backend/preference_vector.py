"""Build a structured preference vector from CLIP, segmentation, and OpenCV outputs."""

from __future__ import annotations

from typing import Any, Dict, Mapping

import numpy as np

SCENE_CATEGORIES = ("beach", "nature", "city", "culture", "fashion", "food")

_UNCERTAIN_THRESHOLD = 0.3

_SEMANTIC_KEYS = (
    ("water_ratio", "water"),
    ("sky_ratio", "sky"),
    ("vegetation_ratio", "vegetation"),
    ("building_ratio", "building"),
    ("food_ratio", "food"),
)

_VISUAL_KEYS = ("brightness", "saturation", "contrast", "warm_tone")


def _clip(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _scene_scores(clip_result: Mapping[str, Any]) -> Dict[str, float]:
    all_scores = clip_result.get("all_scores") or {}
    scene: Dict[str, float] = {}
    for cat in SCENE_CATEGORIES:
        raw = all_scores.get(cat, all_scores.get(cat.capitalize(), 0.0))
        scene[cat] = _clip(float(raw))
    return scene


def build_vector(
    clip_result: Mapping[str, Any],
    segment_result: Mapping[str, float],
    opencv_result: Mapping[str, float],
) -> Dict[str, Any]:
    """
    Merge CLIP classification, Mask2Former ratios, and OpenCV tone metrics
    into a nested preference vector.
    """
    scene = _scene_scores(clip_result)

    visual = {
        key: _clip(float(opencv_result.get(key, 0.0)))
        for key in _VISUAL_KEYS
    }

    semantic = {
        out_key: _clip(float(segment_result.get(seg_key, 0.0)))
        for out_key, seg_key in _SEMANTIC_KEYS
    }

    category = str(clip_result.get("category", "")).lower()
    if category not in SCENE_CATEGORIES and scene:
        category = max(scene, key=scene.get)

    confidence = _clip(float(clip_result.get("confidence", 0.0)))

    return {
        "scene": scene,
        "visual": visual,
        "semantic": semantic,
        "top_category": category,
        "confidence": confidence,
        "is_uncertain": confidence < _UNCERTAIN_THRESHOLD,
    }
