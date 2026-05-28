"""CLIP zero-shot travel category (6 classes)."""

from __future__ import annotations

from typing import Any, Dict, List, Union

from PIL import Image

from .clip_base import clip_zero_shot_scores
from .labels import PLACE_LABELS

CATEGORY_LABELS = PLACE_LABELS

CATEGORY_PROMPTS: Dict[str, List[str]] = {
    "beach": [
        "a photo of a beach vacation with sand and ocean waves",
        "a photo of tropical seaside resort and coastline",
    ],
    "nature": [
        "a photo of mountain forest hiking trail and scenic landscape",
        "a photo of lake waterfall and natural wilderness",
    ],
    "city": [
        "a photo of urban city skyline street and modern buildings",
        "a photo of downtown night view and city architecture",
    ],
    "culture": [
        "a photo of museum art gallery temple and cultural heritage",
        "a photo of historic site traditional architecture and exhibition",
    ],
    "festival": [
        "a photo of music festival concert crowd and stage lights",
        "a photo of outdoor celebration parade fireworks and carnival",
    ],
    "food": [
        "a photo of restaurant dining street food and local cuisine",
        "a photo of cafe meal food travel experience",
    ],
}


def analyze_category(image: Image.Image) -> Dict[str, float]:
    return clip_zero_shot_scores(image, CATEGORY_LABELS, CATEGORY_PROMPTS, "category_v2")


def top_category(scores: Dict[str, float]) -> tuple[str, float]:
    if not scores:
        return "", 0.0
    label = max(scores, key=scores.get)
    return label, float(scores[label])


def classify_with_fallback(
    image: Image.Image,
    *,
    threshold: float = 0.35,
) -> Dict[str, Any]:
    """
    CLIP zero-shot category; if confidence < threshold, enrich with Gemini travel hint.
    """
    scores = analyze_category(image)
    all_scores = {lab: float(scores.get(lab, 0.0)) for lab in CATEGORY_LABELS}
    category, confidence = top_category(scores)

    is_other = confidence < threshold
    other_hint = None
    travel_hint = None
    hint_weight = 0.0

    if is_other:
        from .other_analyzer import analyze_other_as_travel_hint

        other_hint = analyze_other_as_travel_hint(image)
        travel_hint = other_hint.get("travel_hint")
        hint_weight = float(other_hint.get("hint_weight", 0.3))

    return {
        "category": category,
        "confidence": confidence,
        "all_scores": all_scores,
        "is_other": is_other,
        "other_hint": other_hint,
        "travel_hint": travel_hint,
        "hint_weight": hint_weight,
    }
