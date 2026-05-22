"""Refined style pseudo-label rules (hard / weak / discard)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from .labels import STYLE_LABELS

CATEGORY_CONF_HARD = 0.55
CATEGORY_CONF_WEAK = 0.38
CATEGORY_CONF_DISCARD = 0.32
MAX_STYLE_LABELS = 3
CALM_STRONG_EVIDENCE_MIN = 3  # calm needs >2 hits when co-occurring with other styles for hard


def _tags(interest_tags: Sequence[Mapping[str, Any]]) -> Set[str]:
    return {str(t.get("tag", "")) for t in interest_tags if t.get("tag")}


def _tone(visual_tone: Mapping[str, float]) -> Dict[str, float]:
    keys = (
        "brightness",
        "saturation",
        "warm_tone",
        "contrast",
        "blue_tone",
        "green_tone",
        "night_score",
        "person_ratio",
    )
    return {k: float(visual_tone.get(k, 0.0)) for k in keys}


def _allow_calm(t: Mapping[str, float]) -> bool:
    """Calm requires quiet visual tone; exclude busy / vivid scenes."""
    if t.get("person_ratio", 0.0) >= 0.1:
        return False
    if t.get("saturation", 0.0) >= 0.6:
        return False
    return True


def _limit_style_hits(
    hits: List[Tuple[str, str]],
    *,
    max_styles: int = MAX_STYLE_LABELS,
) -> List[Tuple[str, str]]:
    """Keep at most ``max_styles`` labels; prefer styles with more rule evidence."""
    if not hits:
        return hits
    counts: Dict[str, int] = defaultdict(int)
    for style, _ in hits:
        counts[style] += 1
    top_styles = sorted(counts.keys(), key=lambda s: (-counts[s], s))[:max_styles]
    allowed = set(top_styles)
    return [(s, r) for s, r in hits if s in allowed]


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
    calm_added = False

    def add(style: str, rule: str) -> None:
        hits.append((style, rule))
        nonlocal calm_added
        if style == "calm":
            calm_added = True

    if "history" in tags:
        add("local", "tag_history")

    if category in ("festival", "city"):
        if "nightlife" in tags:
            add("energetic", "tag_nightlife")
        if "sports" in tags:
            add("energetic", "tag_sports")

    if category == "food":
        if "cafe" in tags and t.get("warm_tone", 0.0) >= 0.50:
            add("cozy", "food_cafe_warm")
        if (
            "cafe" in tags
            and t.get("warm_tone", 0.0) >= 0.55
            and t.get("contrast", 0.0) <= 0.45
        ):
            add("aesthetic", "food_cafe_aesthetic")
        if "cafe" in tags and t.get("warm_tone", 0.0) >= 0.52:
            add("romantic", "food_cafe_romantic")
        if "local_market" in tags:
            add("local", "food_local_market")
            add("energetic", "food_local_market")

    elif category == "beach":
        if _allow_calm(t) and (
            t.get("brightness", 0.0) >= 0.50
            and t.get("blue_tone", 0.0) >= 0.25
        ):
            add("calm", "beach_calm_tone")
        if t.get("warm_tone", 0.0) >= 0.48:
            add("romantic", "beach_warm")
        if t.get("saturation", 0.0) >= 0.55 and t.get("blue_tone", 0.0) >= 0.40:
            add("aesthetic", "beach_aesthetic")

    elif category == "nature":
        if _allow_calm(t) and (
            (
                t.get("green_tone", 0.0) >= 0.22
                or segment_vegetation >= 0.20
            )
            and t.get("saturation", 0.0) <= 0.55
            and t.get("contrast", 0.0) <= 0.45
        ):
            add("calm", "nature_calm_tone")
        if t.get("contrast", 0.0) >= 0.50:
            add("energetic", "nature_contrast")
        if t.get("warm_tone", 0.0) >= 0.50 and t.get("brightness", 0.0) >= 0.45:
            add("romantic", "nature_warm_bright")

    elif category == "city":
        if t.get("night_score", 0.0) >= 0.32:
            add("energetic", "city_night")
        if t.get("night_score", 0.0) >= 0.25:
            add("aesthetic", "city_night_aesthetic")
        if t.get("night_score", 0.0) >= 0.20 and t.get("warm_tone", 0.0) >= 0.48:
            add("romantic", "city_night_warm")
        if "local_market" in tags:
            add("local", "city_local_market")

    elif category == "culture":
        if subtype == "museum_gallery":
            add("aesthetic", "culture_museum_gallery")
        if "art" in tags:
            add("aesthetic", "culture_art_tag")
        if subtype == "museum_gallery" and "art" in tags:
            add("aesthetic", "culture_museum_art_strong")
        if subtype == "modern_architecture":
            add("aesthetic", "culture_modern_architecture")
        if subtype == "exhibition_performance":
            add("aesthetic", "culture_exhibition_performance")
        if subtype == "pop_culture":
            add("energetic", "culture_pop_energetic")
            add("aesthetic", "culture_pop_aesthetic")
        if subtype == "traditional_architecture":
            add("local", "culture_traditional_architecture")
        if subtype == "historical_site":
            add("local", "culture_historical_local")
            add("aesthetic", "culture_historical_aesthetic")
        if (
            subtype == "traditional_architecture"
            and t.get("warm_tone", 0.0) >= 0.50
        ):
            add("romantic", "culture_traditional_warm")

    elif category == "festival":
        crowd = float(fest.get("crowd_score", fest.get("crowd", 0.0)))
        vivid = float(fest.get("vivid_tone", fest.get("vivid_color", 0.0)))
        night = float(fest.get("night_lighting", 0.0))
        if crowd >= 0.30 or vivid >= 0.45:
            add("energetic", "festival_crowd_vivid")
        if night >= 0.35 or t.get("night_score", 0.0) >= 0.32:
            add("energetic", "festival_night")
            add("aesthetic", "festival_night")

    if calm_added and t.get("warm_tone", 0.0) >= 0.55:
        add("romantic", "calm_warm_combo")

    return _limit_style_hits(hits, max_styles=MAX_STYLE_LABELS)


def _tone_matches(style: str, t: Mapping[str, float]) -> bool:
    if style == "cozy":
        return t.get("warm_tone", 0.0) >= 0.48
    if style == "calm":
        if t.get("person_ratio", 0.0) >= 0.1 or t.get("saturation", 0.0) >= 0.6:
            return False
        beach_calm = (
            t.get("brightness", 0.0) >= 0.50 and t.get("blue_tone", 0.0) >= 0.25
        )
        nature_calm = (
            t.get("green_tone", 0.0) >= 0.22
            and t.get("saturation", 0.0) <= 0.55
            and t.get("contrast", 0.0) <= 0.45
        )
        return beach_calm or nature_calm
    if style == "romantic":
        return t.get("warm_tone", 0.0) >= 0.48
    if style == "energetic":
        return (
            t.get("contrast", 0.0) >= 0.38
            or t.get("night_score", 0.0) >= 0.28
            or t.get("saturation", 0.0) >= 0.42
        )
    if style == "aesthetic":
        return t.get("contrast", 0.0) >= 0.32 or t.get("saturation", 0.0) >= 0.38
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
            "rule_hits": [{"style": s, "rule": r} for s, r in rule_hits],
        }

    ranked = sorted(
        ((s, len(r)) for s, r in style_rules.items()),
        key=lambda x: (-x[1], x[0]),
    )
    primary, evidence_count = ranked[0]
    tone_ok = _tone_matches(primary, _tone(visual_tone))
    candidates = [s for s, _ in ranked[:MAX_STYLE_LABELS]]

    multihot = {s: 0.0 for s in STYLE_LABELS}
    for style in candidates:
        multihot[style] = 1.0

    status = "discard"
    reason: Optional[str] = None

    if evidence_count >= 2 and category_confidence >= CATEGORY_CONF_HARD and tone_ok:
        status = "hard"
    elif evidence_count >= 1 and category_confidence >= CATEGORY_CONF_WEAK:
        status = "weak"
        if evidence_count < 2:
            reason = "single_rule_evidence"
        elif not tone_ok:
            reason = "tone_mismatch"
        elif category_confidence < CATEGORY_CONF_HARD:
            reason = "category_conf_not_hard"
    else:
        reason = "ambiguous_style_rules"
        primary = None
        candidates = []
        multihot = {s: 0.0 for s in STYLE_LABELS}

    # Calm cap: calm co-occurring with other styles needs strong calm evidence for hard
    calm_count = len(style_rules.get("calm", []))
    if (
        "calm" in style_rules
        and len(style_rules) > 1
        and calm_count <= 2
        and status == "hard"
    ):
        status = "weak"
        reason = "calm_cap_weak"

    return {
        "refined_style_label": primary,
        "style_candidates": candidates,
        "style_multihot": multihot,
        "label_status": status,
        "discard_reason": reason,
        "rule_hits": [{"style": s, "rule": r} for s, r in rule_hits],
        "style_rule_counts": {s: len(rs) for s, rs in style_rules.items()},
        "primary_evidence_count": evidence_count,
        "tone_matches_primary": tone_ok,
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
