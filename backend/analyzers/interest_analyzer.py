"""CLIP zero-shot interest scoring."""

from __future__ import annotations

from typing import Dict

from PIL import Image

try:
    from .clip_base import clip_zero_shot_scores
except ImportError:
    from analyzers.clip_base import clip_zero_shot_scores

INTEREST_LABELS = [
    "sports",
    "anime",
    "disney",
    "movie",
    "gaming",
    "theme_park",
]

INTEREST_PROMPTS: Dict[str, str] = {
    "sports": "a photo of exercise competition and active sport hobbies",
    "anime": "a photo of anime fandom and Japanese character culture",
    "disney": (
        "a photo of disney theme park fantasy castle characters or magic kingdom"
    ),
    "movie": "a photo of watching films or movie culture venue",
    "gaming": "a photo of digital games esports or arcade culture",
    "theme_park": (
        "a photo of amusement park roller coaster rides or attractions"
    ),
}


def analyze_interest(image: Image.Image) -> Dict[str, float]:
    return clip_zero_shot_scores(image, INTEREST_LABELS, INTEREST_PROMPTS, "interest")
