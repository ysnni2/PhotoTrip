"""CLIP zero-shot place category scoring."""

from __future__ import annotations

from typing import Dict

from PIL import Image

try:
    from .clip_base import clip_zero_shot_scores
except ImportError:  # direct script / non-package run
    from analyzers.clip_base import clip_zero_shot_scores

PLACE_LABELS = ["beach", "nature", "city", "food", "festival", "culture"]

PLACE_PROMPTS: Dict[str, str] = {
    "beach": (
        "a photo of beach vacation with sandy shore ocean waves surfing "
        "or tropical resort"
    ),
    "nature": (
        "a photo of mountain forest hiking trail lake waterfall "
        "or scenic natural landscape"
    ),
    "city": (
        "a photo of urban city skyline street buildings night view subway "
        "or modern architecture"
    ),
    "food": "a photo of eating, dining, and food travel experience",
    "festival": (
        "a photo of music festival concert fireworks outdoor celebration crowd "
        "or street parade"
    ),
    "culture": (
        "a photo of museum art gallery exhibition temple ancient ruins "
        "cultural heritage or historic site"
    ),
}


def analyze_place(image: Image.Image) -> Dict[str, float]:
    return clip_zero_shot_scores(image, PLACE_LABELS, PLACE_PROMPTS, "place")
