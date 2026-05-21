"""Culture subtype CLIP ensemble classifier."""

from __future__ import annotations

from typing import Any, Dict, List

from PIL import Image

from .clip_base import clip_zero_shot_scores
from .labels import CULTURE_SUBTYPE_LABELS

CULTURE_SUBTYPE_PROMPTS: Dict[str, List[str]] = {
    "museum_gallery": [
        "a photo inside an art museum or gallery exhibition",
        "a photo of paintings sculptures displayed in a museum",
        "a photo of contemporary art gallery white cube space",
        "a photo of museum visitors viewing framed artwork",
    ],
    "historical_site": [
        "a photo of ancient ruins historic monument or heritage site",
        "a photo of archaeological site old castle or memorial",
        "a photo of UNESCO world heritage landmark outdoors",
    ],
    "traditional_architecture": [
        "a photo of traditional temple shrine hanok or old town street",
        "a photo of historic cultural architecture and heritage building",
    ],
    "modern_architecture": [
        "a photo of modern skyscraper contemporary building and urban design",
        "a photo of futuristic architecture glass tower and city landmark",
    ],
    "pop_culture": [
        "a photo of pop culture shop street art anime district",
        "a photo of youth culture entertainment district and colorful signage",
    ],
    "exhibition_performance": [
        "a photo of live performance theater concert hall or cultural show",
        "a photo of exhibition opening stage performance indoors",
    ],
}

SUBTYPE_CONFIDENCE_MIN = 0.25


def score_culture_subtypes(image: Image.Image) -> Dict[str, float]:
    return clip_zero_shot_scores(
        image, CULTURE_SUBTYPE_LABELS, CULTURE_SUBTYPE_PROMPTS, "culture_subtype_v2"
    )


def analyze_culture(image: Image.Image) -> Dict[str, Any]:
    scores = score_culture_subtypes(image)
    rounded = {k: round(float(v), 4) for k, v in scores.items()}
    top = max(rounded, key=rounded.get) if rounded else ""
    conf = float(rounded.get(top, 0.0))
    confident = conf >= SUBTYPE_CONFIDENCE_MIN
    return {
        "culture_subtype_scores": rounded,
        "top_culture_subtype": top if confident else None,
        "culture_confidence": round(conf, 4),
        "gemini_fallback_needed": not confident,
    }
