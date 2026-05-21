"""CLIP zero-shot interest (legacy 6-way + recommendation 9 tags)."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from PIL import Image

try:
    from .clip_base import clip_zero_shot_scores
    from .labels import INTEREST_TAG_LABELS
except ImportError:
    from analyzers.clip_base import clip_zero_shot_scores
    from analyzers.labels import INTEREST_TAG_LABELS

INTEREST_LABELS = [
    "sports", "anime", "disney", "movie", "gaming", "theme_park",
]

INTEREST_PROMPTS: Dict[str, str] = {
    "sports": "a photo of exercise competition and active sport hobbies",
    "anime": "a photo of anime fandom and Japanese character culture",
    "disney": "a photo of disney theme park fantasy castle characters or magic kingdom",
    "movie": "a photo of watching films or movie culture venue",
    "gaming": "a photo of digital games esports or arcade culture",
    "theme_park": "a photo of amusement park roller coaster rides or attractions",
}

INTEREST_TAG_PROMPTS: Dict[str, List[str]] = {
    "anime": ["a photo of anime merchandise cosplay and japanese otaku culture"],
    "disney_themepark": ["a photo of disney theme park castle characters and fantasy parade"],
    "sports": ["a photo of stadium sports event and athletic competition"],
    "cafe": ["a photo of cozy cafe coffee shop interior and latte art"],
    "shopping": ["a photo of shopping street mall boutique and retail district"],
    "nightlife": ["a photo of nightclub bar neon lights night entertainment district"],
    "art": ["a photo of street art mural graffiti and creative installation"],
    "history": ["a photo of historic landmark old town heritage walking tour"],
    "local_market": ["a photo of local street market vendors fresh produce and alley food"],
}

TAG_THRESHOLD = 0.15
TAG_TOP_K = 3


def analyze_interest(image: Image.Image) -> Dict[str, float]:
    return clip_zero_shot_scores(image, INTEREST_LABELS, INTEREST_PROMPTS, "interest_legacy")


def score_interest_tags(image: Image.Image) -> Dict[str, float]:
    return clip_zero_shot_scores(
        image, INTEREST_TAG_LABELS, INTEREST_TAG_PROMPTS, "interest_tags_v1"
    )


def select_interest_tags(
    scores: Mapping[str, float],
    *,
    threshold: float = TAG_THRESHOLD,
    top_k: int = TAG_TOP_K,
) -> List[Dict[str, Any]]:
    k = max(2, min(3, int(top_k)))
    ranked = sorted(scores.items(), key=lambda x: -float(x[1]))
    tags: List[Dict[str, Any]] = []
    for tag, score in ranked[:k]:
        if float(score) < threshold:
            continue
        tags.append({"tag": tag, "score": round(float(score), 4)})
    return tags


def extract_interest_tags(
    image: Image.Image,
    *,
    threshold: float = TAG_THRESHOLD,
    top_k: int = TAG_TOP_K,
) -> Dict[str, List[Dict[str, Any]]]:
    scores = score_interest_tags(image)
    return {"interest_tags": select_interest_tags(scores, threshold=threshold, top_k=top_k)}
