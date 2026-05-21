"""Ensemble CLIP zero-shot + BCE MLP multi-label scores."""

from __future__ import annotations

from typing import Dict, Mapping, Optional

import torch
from PIL import Image

from .labels import MOOD_LABELS, PLACE_LABELS
from .mlp_head import clip_pooler_features, load_mlp_head, mlp_multilabel_probs
from .mood_analyzer import analyze_mood
from .place_analyzer import analyze_place


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


def ensemble_mood_scores(
    image: Image.Image,
    *,
    mlp_weight: float = 0.55,
) -> Dict[str, float]:
    clip_s = analyze_mood(image)
    head = load_mlp_head("mlp_mood_best.pth", num_classes=len(MOOD_LABELS))
    mlp_p = mlp_multilabel_probs(head, clip_pooler_features(image)) if head else None
    return _blend(clip_s, mlp_p, MOOD_LABELS, mlp_weight=mlp_weight)


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
