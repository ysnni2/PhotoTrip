"""Build a structured preference vector from CLIP, segmentation, and OpenCV outputs."""

from __future__ import annotations

from typing import Any, Dict, Mapping

import numpy as np

SCENE_CATEGORIES = ("beach", "nature", "city", "culture", "festival", "food")

_UNCERTAIN_THRESHOLD = 0.3
_STYLE_UNCERTAIN_THRESHOLD = 0.15

_SEMANTIC_KEYS = (
    ("water_ratio", "water"),
    ("sky_ratio", "sky"),
    ("vegetation_ratio", "vegetation"),
    ("building_ratio", "building"),
    ("food_ratio", "food"),
)

_VISUAL_KEYS = (
    "brightness",
    "saturation",
    "contrast",
    "warm_tone",
    "person_ratio",
    "animal_ratio",
)


def _clip(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _scene_scores(clip_result: Mapping[str, Any]) -> Dict[str, float]:
    all_scores = clip_result.get("all_scores") or {}
    scene: Dict[str, float] = {}
    for cat in SCENE_CATEGORIES:
        raw = all_scores.get(cat, all_scores.get(cat.capitalize(), 0.0))
        scene[cat] = _clip(float(raw))
    return scene


def _apply_other_travel_hint(
    scene: Dict[str, float],
    clip_result: Mapping[str, Any],
) -> Dict[str, float]:
    """Blend Gemini travel_hint at hint_weight (weaker than primary CLIP scores)."""
    if not clip_result.get("is_other"):
        return scene

    other = clip_result.get("other_hint") or {}
    hint = clip_result.get("travel_hint")
    if hint is None:
        hint = other.get("travel_hint")
    hint = str(hint or "").strip().lower()
    if hint not in SCENE_CATEGORIES:
        return scene

    weight = clip_result.get("hint_weight", other.get("hint_weight", 0.3))
    weight = max(0.1, min(0.5, float(weight)))

    out = dict(scene)
    out[hint] = _clip(out.get(hint, 0.0) + weight)
    return out


def _style_scores(style_result: Mapping[str, float]) -> Dict[str, float]:
    return {key: _clip(float(value)) for key, value in style_result.items()}


def build_vector(
    clip_result: Mapping[str, Any],
    segment_result: Mapping[str, float],
    opencv_result: Mapping[str, float],
    style_result: Mapping[str, float],
    lifestyle_result: Mapping[str, Any] = {},
) -> Dict[str, Any]:
    """
    Merge SigLIP scene classification, style scores, Mask2Former ratios,
    and OpenCV tone metrics into a nested preference vector.
    """
    scene = _apply_other_travel_hint(_scene_scores(clip_result), clip_result)

    visual = {
        key: _clip(float(opencv_result.get(key, 0.0)))
        for key in _VISUAL_KEYS
    }

    semantic = {
        out_key: _clip(float(segment_result.get(seg_key, 0.0)))
        for out_key, seg_key in _SEMANTIC_KEYS
    }

    style = _style_scores(style_result)

    category = str(clip_result.get("category", "")).lower()
    if category not in SCENE_CATEGORIES and scene:
        category = max(scene, key=scene.get)

    confidence = _clip(float(clip_result.get("confidence", 0.0)))
    max_style = max(style.values()) if style else 0.0
    is_uncertain = (
        confidence < _UNCERTAIN_THRESHOLD
        or max_style < _STYLE_UNCERTAIN_THRESHOLD
    )

    other_hint = clip_result.get("other_hint") if clip_result.get("is_other") else None

    return {
        "scene": scene,
        "visual": visual,
        "semantic": semantic,
        "style": style,
        "lifestyle": dict(lifestyle_result),
        "top_category": category,
        "confidence": confidence,
        "is_uncertain": is_uncertain,
        "is_other": bool(clip_result.get("is_other")),
        "other_hint": other_hint,
    }
