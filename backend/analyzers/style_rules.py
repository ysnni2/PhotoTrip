"""Refined style pseudo-label rules (hard / weak / discard)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from .labels import STYLE_LABELS

CATEGORY_CONF_HARD = 0.55
CATEGORY_CONF_WEAK = 0.38
CATEGORY_CONF_DISCARD = 0.32


def _tags(interest_tags: Sequence[Mapping[str, Any]]) -> Set[str]:
    return {str(t.get("tag", "")) for t in interest_tags if t.get("tag")}


def _tone(visual_tone: Mapping[str, float]) -> Dict[str, float]:
    keys = (
        "brightness", "saturation", "warm_tone", "contrast",
        "blue_tone", "green_tone", "night_score",
    )
    return {k: float(visual_tone.get(k, 0.0)) for k in keys}


def collect_style_rule_hits(
    *,
    category: str,
    culture_subtype: Optional[str],
    interest_tags: Sequence[Mapping[str, Any]],
    visual_tone: Mapping[str, float],
    festival_evidence: Optional[Mapping[str, float]] = None,
    segment_vegetation: float = 0.0,
) -> List[Tuple[str, str]]:
    tags = _tags(interest_tags)
    t = _tone(visual_tone)
    fest = festival_evidence or {}
    subtype = culture_subtype or ""
    hits: List[Tuple[str, str]] = []

    def add(style: str, rule: str) -> None:
        hits.append((style, rule))

    if category == "food":
        if "cafe" in tags and t.get("warm_tone", 0) >= 0.50:
            add("cozy", "food_cafe_warm")
            add("aesthetic", "food_cafe_warm")
        if "local_market" in tags:
            add("local", "food_local_market")
            add("energetic", "food_local_market")

    elif category == "beach":
        if t.get("brightness", 0) >= 0.52 and t.get("blue_tone", 0) >= 0.22:
            add("calm", "beach_bright_blue")
        if t.get("warm_tone", 0) >= 0.52:
            add("romantic", "beach_warm")

    elif category == "nature":
        if t.get("green_tone", 0) >= 0.22 or segment_vegetation >= 0.25:
            add("calm", "nature_green")
        if t.get("contrast", 0) >= 0.45:
            add("energetic", "nature_contrast")

    elif category == "city":
        if t.get("night_score", 0) >= 0.32:
            add("energetic", "city_night")
            add("aesthetic", "city_night")
        if "local_market" in tags:
            add("local", "city_local_market")

    elif category == "culture":
        if subtype == "museum_gallery" or "art" in tags:
            add("aesthetic", "culture_museum_art")
        if subtype == "historical_site":
            add("local", "culture_historical")
            add("aesthetic", "culture_historical")
        if subtype == "pop_culture":
            add("energetic", "culture_pop")
            add("aesthetic", "culture_pop")

    elif category == "festival":
        crowd = float(fest.get("crowd_score", fest.get("crowd", 0.0)))
        vivid = float(fest.get("vivid_tone", fest.get("vivid_color", 0.0)))
        night = float(fest.get("night_lighting", 0.0))
        if crowd >= 0.30 or vivid >= 0.45:
            add("energetic", "festival_crowd_vivid")
        if night >= 0.35 or t.get("night_score", 0) >= 0.32:
            add("energetic", "festival_night")
            add("aesthetic", "festival_night")

    return hits


def _tone_matches(style: str, t: Mapping[str, float]) -> bool:
    if style == "cozy":
        return t.get("warm_tone", 0) >= 0.48
    if style == "calm":
        return (
            t.get("brightness", 0) >= 0.42
            or t.get("blue_tone", 0) >= 0.18
            or t.get("green_tone", 0) >= 0.18
        )
    if style == "romantic":
        return t.get("warm_tone", 0) >= 0.52
    if style == "energetic":
        return (
            t.get("contrast", 0) >= 0.38
            or t.get("night_score", 0) >= 0.28
            or t.get("saturation", 0) >= 0.42
        )
    if style == "aesthetic":
        return t.get("contrast", 0) >= 0.35 or t.get("saturation", 0) >= 0.38
    return True


def assign_refined_style(
    *,
    category: str,
    category_confidence: float,
    culture_subtype: Optional[str],
    interest_tags: Sequence[Mapping[str, Any]],
    visual_tone: Mapping[str, float],
    festival_evidence: Optional[Mapping[str, float]] = None,
    segment_vegetation: float = 0.0,
) -> Dict[str, Any]:
    rule_hits = collect_style_rule_hits(
        category=category,
        culture_subtype=culture_subtype,
        interest_tags=interest_tags,
        visual_tone=visual_tone,
        festival_evidence=festival_evidence,
        segment_vegetation=segment_vegetation,
    )
    style_rules: Dict[str, List[str]] = defaultdict(list)
    for style, rule in rule_hits:
        style_rules[style].append(rule)

    if category_confidence < CATEGORY_CONF_DISCARD or not rule_hits:
        return {
            "refined_style_label": None,
            "style_candidates": [],
            "style_multihot": {s: 0.0 for s in STYLE_LABELS},
            "label_status": "discard",
            "discard_reason": "low_confidence_or_no_rules",
            "rule_hits": rule_hits,
        }

    ranked = sorted(((s, len(r)) for s, r in style_rules.items()), key=lambda x: -x[1])
    primary, evidence_count = ranked[0]
    tone_ok = _tone_matches(primary, _tone(visual_tone))
    candidates = [s for s, _ in ranked[:3]]

    multihot = {s: 0.0 for s in STYLE_LABELS}
    for style in candidates:
        multihot[style] = 1.0
    multihot[primary] = 1.0

    if evidence_count >= 2 and category_confidence >= CATEGORY_CONF_HARD and tone_ok:
        status = "hard"
        reason = None
    elif evidence_count >= 1 and category_confidence >= CATEGORY_CONF_WEAK:
        status = "weak"
        reason = "single_rule" if evidence_count < 2 else "tone_or_conf"
    else:
        status = "discard"
        reason = "ambiguous"
        primary = None
        candidates = []

    return {
        "refined_style_label": primary,
        "style_candidates": candidates,
        "style_multihot": multihot,
        "label_status": status,
        "discard_reason": reason,
        "rule_hits": [{"style": s, "rule": r} for s, r in rule_hits],
        "primary_evidence_count": evidence_count,
    }


def scores_to_multihot(
    scores: Mapping[str, float],
    labels: Sequence[str],
    *,
    threshold: float = 0.20,
    top_k: int = 2,
) -> Dict[str, float]:
    ranked = sorted(
        ((lab, float(scores.get(lab, 0.0))) for lab in labels),
        key=lambda x: -x[1],
    )
    out = {lab: 0.0 for lab in labels}
    for lab, sc in ranked[:top_k]:
        if sc >= threshold:
            out[lab] = 1.0
    if not any(out.values()) and ranked:
        out[ranked[0][0]] = 1.0
    return out
