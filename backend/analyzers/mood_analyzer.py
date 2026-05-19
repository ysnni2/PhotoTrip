"""CLIP zero-shot mood scoring."""

from __future__ import annotations

from typing import Dict

from PIL import Image

try:
    from .clip_base import clip_zero_shot_scores
except ImportError:
    from analyzers.clip_base import clip_zero_shot_scores

MOOD_LABELS = ["calm", "cozy", "romantic", "energetic", "local", "aesthetic"]

MOOD_PROMPTS: Dict[str, str] = {
    "calm": "a photo of a slow restful and healing travel atmosphere",
    "cozy": (
        "a warm cozy indoor cafe blanket soft lighting or home interior"
    ),
    "romantic": (
        "a romantic sunset golden hour flowers couple or dreamy atmosphere"
    ),
    "energetic": (
        "an energetic active sports party dancing or vibrant crowd scene"
    ),
    "local": (
        "an authentic local neighborhood market alley everyday life scene"
    ),
    "aesthetic": (
        "a photo of a carefully composed aesthetic visual style with balanced "
        "composition color harmony beautiful lighting curated stylish and "
        "visually pleasing scene"
    ),
}


def analyze_mood(image: Image.Image) -> Dict[str, float]:
    return clip_zero_shot_scores(image, MOOD_LABELS, MOOD_PROMPTS, "mood")
