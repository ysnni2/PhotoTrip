"""Unified visual evidence for pseudo-label generation and inference."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

import torch
from PIL import Image

from .category_analyzer import CATEGORY_LABELS, analyze_category, top_category
from .culture_analyzer import analyze_culture
from .festival_analyzer import analyze_festival
from .interest_analyzer import extract_interest_tags, score_interest_tags
from .labels import MOOD_LABELS, PLACE_LABELS
from .mood_analyzer import analyze_mood
from .style_rules import assign_refined_style, scores_to_multihot


def _segment_boosts(segment_result: Mapping[str, float]) -> Dict[str, float]:
    boosts = {label: 0.0 for label in CATEGORY_LABELS}
    sky = float(segment_result.get("sky", 0.0))
    tree = float(segment_result.get("tree", 0.0))
    building = float(segment_result.get("building", 0.0))
    water = float(segment_result.get("water", 0.0))
    food = float(segment_result.get("food", 0.0))
    vegetation = float(segment_result.get("vegetation", 0.0))
    if sky > 0.5 and tree > 0.05:
        boosts["nature"] += 0.3
    if sky > 0.5 and building > 0.1:
        boosts["city"] += 0.2
    if water > 0.2:
        boosts["beach"] += 0.4
    if food > 0.1:
        boosts["food"] += 0.4
    if vegetation > 0.3:
        boosts["nature"] += 0.3
    return boosts


def _fuse_category(
    clip_scores: Mapping[str, float],
    segment_result: Optional[Mapping[str, float]],
) -> Dict[str, float]:
    if not segment_result:
        return dict(clip_scores)
    boosts = _segment_boosts(segment_result)
    adjusted = {
        lab: float(clip_scores.get(lab, 0.0)) + boosts[lab] for lab in CATEGORY_LABELS
    }
    vals = torch.tensor([adjusted[lab] for lab in CATEGORY_LABELS], dtype=torch.float32)
    probs = torch.softmax(vals, dim=0)
    return {CATEGORY_LABELS[i]: float(probs[i]) for i in range(len(CATEGORY_LABELS))}


def _visual_tone(opencv_result: Mapping[str, float]) -> Dict[str, float]:
    keys = (
        "brightness", "saturation", "warm_tone", "contrast",
        "blue_tone", "green_tone", "night_score",
    )
    return {k: round(float(opencv_result.get(k, 0.0)), 4) for k in keys}


def extract_visual_evidence(
    image: Image.Image,
    *,
    opencv_result: Optional[Mapping[str, float]] = None,
    segment_result: Optional[Mapping[str, float]] = None,
    use_gemini_festival: bool = True,
) -> Dict[str, Any]:
    if opencv_result is None:
        from opencv_analyzer import analyze as analyze_opencv

        opencv_result = analyze_opencv(image)

    clip_scores = analyze_category(image)
    if segment_result:
        clip_scores = _fuse_category(clip_scores, segment_result)
    category, cat_conf = top_category(clip_scores)
    category_scores = {k: round(float(clip_scores.get(k, 0.0)), 4) for k in CATEGORY_LABELS}

    culture_block: Dict[str, Any] = {
        "culture_subtype_scores": {},
        "top_culture_subtype": None,
        "culture_confidence": 0.0,
        "gemini_fallback_needed": False,
    }
    if category == "culture":
        culture_block = analyze_culture(image)

    interest_tags = extract_interest_tags(image)["interest_tags"]
    festival_block = analyze_festival(
        image, opencv_result=opencv_result, category_scores=category_scores, use_gemini=use_gemini_festival
    )
    visual_tone = _visual_tone(opencv_result)
    seg_veg = float((segment_result or {}).get("vegetation", 0.0))

    style_block = assign_refined_style(
        category=category,
        category_confidence=cat_conf,
        culture_subtype=culture_block.get("top_culture_subtype"),
        interest_tags=interest_tags,
        visual_tone=visual_tone,
        festival_evidence=festival_block.get("festival_evidence"),
        segment_vegetation=seg_veg,
    )

    place_mood_clip = {
        "place_vector": analyze_category(image),
        "mood_vector": analyze_mood(image),
    }
    place_multihot = scores_to_multihot(category_scores, PLACE_LABELS, threshold=0.18, top_k=2)
    mood_multihot = scores_to_multihot(place_mood_clip["mood_vector"], MOOD_LABELS, threshold=0.18, top_k=2)

    return {
        "category": category,
        "category_confidence": round(cat_conf, 4),
        "category_scores": category_scores,
        **culture_block,
        "interest_tags": interest_tags,
        "visual_tone": visual_tone,
        **festival_block,
        **style_block,
        "place_multihot": place_multihot,
        "mood_multihot": mood_multihot,
        "place_vector": place_mood_clip["place_vector"],
        "mood_vector": place_mood_clip["mood_vector"],
    }
