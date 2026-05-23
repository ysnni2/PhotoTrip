"""Ensemble CLIP zero-shot + BCE MLP multi-label scores."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

import torch
from PIL import Image

from .category_analyzer import analyze_category, top_category
from .culture_analyzer import analyze_culture
from .labels import MOOD_LABELS, PLACE_LABELS
from .mlp_head import clip_pooler_features, load_mlp_head, mlp_multilabel_probs
from .mood_analyzer import analyze_mood
from .place_analyzer import analyze_place

CULTURE_CALM_CAP = 0.3

# Culture subtype → mood prior (replaces CLIP mood when category is culture).
CULTURE_MOOD_BY_SUBTYPE: Dict[str, Dict[str, float]] = {
    "museum_gallery": {"aesthetic": 0.7, "local": 0.5},
    "historical_site": {"local": 0.7, "aesthetic": 0.4},
    "traditional_architecture": {"local": 0.6, "aesthetic": 0.4},
    "modern_architecture": {"aesthetic": 0.7},
    "pop_culture": {"energetic": 0.7, "aesthetic": 0.5},
    "exhibition_performance": {"aesthetic": 0.6},
}


def _blend(
    clip_scores: Mapping[str, float],
    mlp_probs: Optional[torch.Tensor],
    labels: list[str],
    *,
    mlp_weight: float = 0.55,
) -> Dict[str, float]:
    out: Dict[str, float] = {}
    cw = 1.0 - mlp_weight
    for i, lab in enumerate(labels):
        c = float(clip_scores.get(lab, 0.0))
        m = float(mlp_probs[i]) if mlp_probs is not None else c
        out[lab] = round(cw * c + mlp_weight * m, 4)
    return out


def ensemble_place_scores(
    image: Image.Image,
    *,
    mlp_weight: float = 0.55,
) -> Dict[str, float]:
    clip_s = analyze_place(image)
    head = load_mlp_head("mlp_place_best.pth", num_classes=len(PLACE_LABELS))
    mlp_p = mlp_multilabel_probs(head, clip_pooler_features(image)) if head else None
    return _blend(clip_s, mlp_p, PLACE_LABELS, mlp_weight=mlp_weight)


def _culture_mood_scores(subtype: Optional[str]) -> Dict[str, float]:
    scores = {lab: 0.0 for lab in MOOD_LABELS}
    if subtype and subtype in CULTURE_MOOD_BY_SUBTYPE:
        for lab, val in CULTURE_MOOD_BY_SUBTYPE[subtype].items():
            if lab in scores:
                scores[lab] = float(val)
    scores["calm"] = min(float(scores.get("calm", 0.0)), CULTURE_CALM_CAP)
    return scores


def _mood_clip_base(image: Image.Image) -> Dict[str, float]:
    category, _ = top_category(analyze_category(image))
    if category != "culture":
        return analyze_mood(image)

    culture = analyze_culture(image)
    subtype = culture.get("top_culture_subtype")
    if subtype:
        return _culture_mood_scores(str(subtype))

    clip_s = analyze_mood(image)
    clip_s = dict(clip_s)
    clip_s["calm"] = min(float(clip_s.get("calm", 0.0)), CULTURE_CALM_CAP)
    return clip_s


def ensemble_mood_scores(
    image: Image.Image,
    *,
    mlp_weight: float = 0.55,
) -> Dict[str, float]:
    clip_s = _mood_clip_base(image)
    head = load_mlp_head("mlp_mood_best.pth", num_classes=len(MOOD_LABELS))
    mlp_p = mlp_multilabel_probs(head, clip_pooler_features(image)) if head else None
    blended = _blend(clip_s, mlp_p, MOOD_LABELS, mlp_weight=mlp_weight)
    category, _ = top_category(analyze_category(image))
    if category == "culture":
        blended["calm"] = round(min(float(blended.get("calm", 0.0)), CULTURE_CALM_CAP), 4)
    return blended


def ensemble_multilabel(
    image: Image.Image,
    *,
    mlp_weight: float = 0.55,
    threshold: float = 0.35,
) -> Dict[str, Any]:
    place_scores = ensemble_place_scores(image, mlp_weight=mlp_weight)
    mood_scores = ensemble_mood_scores(image, mlp_weight=mlp_weight)
    place_active = [k for k, v in place_scores.items() if v >= threshold]
    mood_active = [k for k, v in mood_scores.items() if v >= threshold]
    return {
        "place_scores": place_scores,
        "mood_scores": mood_scores,
        "place_active": place_active or [max(place_scores, key=place_scores.get)],
        "mood_active": mood_active or [max(mood_scores, key=mood_scores.get)],
        "mlp_weight": mlp_weight,
        "threshold": threshold,
    }
