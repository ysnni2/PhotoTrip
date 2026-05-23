"""Refined style pseudo-label rules (hard / weak / discard)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from .labels import STYLE_LABELS

CATEGORY_CONF_HARD = 0.55
CATEGORY_CONF_WEAK = 0.38
CATEGORY_CONF_DISCARD = 0.32
MAX_STYLE_LABELS = 3
COZY_PROTECT_IN_LIMIT = True  # keep cozy in top styles when any cozy rule fires

WARM_COZY_MIN = 0.42
FOOD_COZY_WARM_STRONG = 0.52
FOOD_COZY_WARM_CAFE = 0.50
FOOD_COZY_WARM_MARKET = 0.48
NATURE_COZY_GREEN_MIN = 0.20
NATURE_COZY_WARM_MIN = 0.48
NATURE_COZY_CONTRAST_MAX = 0.40
BEACH_COZY_WARM_MIN = 0.48
CULTURE_COZY_WARM_MIN = 0.48
WARM_ROMANTIC_MIN = 0.46
LOW_CONTRAST_COZY = 0.48
LOW_CONTRAST_ROMANTIC = 0.46
FOOD_COZY_ITEMS = ("dessert", "coffee", "bread")


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
        "indoor_score",
    )
    return {k: float(visual_tone.get(k, 0.0)) for k in keys}


def _food_cozy_items(visual_tone: Mapping[str, float]) -> Set[str]:
    raw = visual_tone.get("food_cozy_items", [])
    if isinstance(raw, str):
        return {raw} if raw in FOOD_COZY_ITEMS else set()
    if isinstance(raw, (list, tuple, set)):
        return {str(x) for x in raw if str(x) in FOOD_COZY_ITEMS}
    return set()


def _has_cozy_anchor(
    *,
    category: str,
    culture_subtype: Optional[str],
    tags: Set[str],
    t: Mapping[str, float],
    visual_tone: Mapping[str, float],
) -> bool:
    """At least one cozy evidence: warm tone, cafe/food, indoor, or food item hint."""
    if t.get("warm_tone", 0.0) >= WARM_COZY_MIN:
        return True
    if "cafe" in tags:
        return True
    if category == "food":
        return True
    if category == "nature" and t.get("green_tone", 0.0) >= NATURE_COZY_GREEN_MIN:
        return True
    if category == "beach" and _allow_calm(t):
        return True
    if category == "culture" and (culture_subtype or "") in (
        "traditional_architecture",
        "historical_site",
    ):
        return True
    if float(visual_tone.get("indoor_score", 0.0)) >= 0.35:
        return True
    if _food_cozy_items(visual_tone):
        return True
    return False


def _maybe_add_cozy(
    hits: List[Tuple[str, str]],
    *,
    category: str,
    culture_subtype: Optional[str],
    tags: Set[str],
    t: Mapping[str, float],
    visual_tone: Mapping[str, float],
    rule: str,
) -> None:
    if _has_cozy_anchor(
        category=category,
        culture_subtype=culture_subtype,
        tags=tags,
        t=t,
        visual_tone=visual_tone,
    ):
        hits.append(("cozy", rule))


def _allow_calm(t: Mapping[str, float]) -> bool:
    if t.get("person_ratio", 0.0) >= 0.12:
        return False
    if t.get("saturation", 0.0) >= 0.62:
        return False
    return True


def _low_crowd(t: Mapping[str, float]) -> bool:
    return t.get("person_ratio", 0.0) < 0.12


def _limit_style_hits(
    hits: List[Tuple[str, str]],
    *,
    max_styles: int = MAX_STYLE_LABELS,
) -> List[Tuple[str, str]]:
    """Cap distinct style labels; reserve a slot for cozy when any cozy rule matched."""
    if not hits:
        return hits
    counts: Dict[str, int] = defaultdict(int)
    for style, _ in hits:
        counts[style] += 1
    ranked = sorted(counts.keys(), key=lambda s: (-counts[s], s))
    allowed: List[str] = []
    if COZY_PROTECT_IN_LIMIT and "cozy" in counts and "cozy" not in allowed:
        allowed.append("cozy")
    for style in ranked:
        if style in allowed:
            continue
        if len(allowed) >= max_styles:
            break
        allowed.append(style)
    allowed_set = set(allowed)
    return [(s, r) for s, r in hits if s in allowed_set]


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
    food_items = _food_cozy_items(visual_tone)

    def add(style: str, rule: str) -> None:
        hits.append((style, rule))
        nonlocal calm_added
        if style == "calm":
            calm_added = True

    def cozy(rule: str) -> None:
        _maybe_add_cozy(
            hits,
            category=category,
            culture_subtype=subtype or None,
            tags=tags,
            t=t,
            visual_tone=visual_tone,
            rule=rule,
        )

    if "history" in tags:
        add("local", "tag_history")

    if category in ("festival", "city"):
        if "nightlife" in tags:
            add("energetic", "tag_nightlife")
        if "sports" in tags:
            add("energetic", "tag_sports")

    # --- Cozy (each match recorded as rule_hits: {style: cozy, rule: <name>}) ---
    if category == "food":
        # legacy: cafe + warm
        if "cafe" in tags and t.get("warm_tone", 0.0) >= FOOD_COZY_WARM_CAFE:
            cozy("food_cafe_warm_cozy")
        if t.get("warm_tone", 0.0) >= FOOD_COZY_WARM_STRONG:
            cozy("food_warm_strong_cozy")
        if "local_market" in tags and t.get("warm_tone", 0.0) >= FOOD_COZY_WARM_MARKET:
            cozy("food_local_market_warm_cozy")
        if food_items:
            cozy("food_item_cozy")
        if (
            "cafe" in tags
            and t.get("warm_tone", 0.0) >= 0.55
            and t.get("contrast", 0.0) <= 0.45
        ):
            add("aesthetic", "food_cafe_aesthetic")
        if "cafe" in tags and t.get("warm_tone", 0.0) >= 0.50:
            add("romantic", "food_cafe_romantic")
        if "local_market" in tags:
            add("local", "food_local_market")
            add("energetic", "food_local_market")

    if "cafe" in tags and t.get("warm_tone", 0.0) >= WARM_COZY_MIN:
        cozy("tag_cafe_warm_cozy")

    indoor = float(visual_tone.get("indoor_score", 0.0)) >= 0.35
    if indoor and t.get("warm_tone", 0.0) >= WARM_COZY_MIN and t.get("contrast", 0.0) <= LOW_CONTRAST_COZY:
        cozy("indoor_warm_low_contrast")

    if category == "city":
        if t.get("night_score", 0.0) >= 0.32:
            add("energetic", "city_night")
        if t.get("night_score", 0.0) >= 0.25:
            add("aesthetic", "city_night_aesthetic")
        if t.get("night_score", 0.0) >= 0.20 and t.get("warm_tone", 0.0) >= 0.48:
            add("romantic", "city_night_warm")
        if (
            t.get("night_score", 0.0) >= 0.18
            and t.get("warm_tone", 0.0) >= WARM_COZY_MIN
            and t.get("contrast", 0.0) <= LOW_CONTRAST_COZY
        ):
            cozy("city_night_warm_cozy")
        if ("cafe" in tags or "shopping" in tags) and t.get("warm_tone", 0.0) >= WARM_COZY_MIN:
            cozy("city_cafe_shopping_warm")
        if "local_market" in tags:
            add("local", "city_local_market")

    elif category == "beach":
        if _allow_calm(t) and (
            t.get("brightness", 0.0) >= 0.50
            and t.get("blue_tone", 0.0) >= 0.25
        ):
            add("calm", "beach_calm_tone")
        if _allow_calm(t) and (
            t.get("saturation", 0.0) <= 0.52
            and t.get("contrast", 0.0) <= 0.48
            and t.get("blue_tone", 0.0) >= 0.20
        ):
            add("calm", "beach_low_sat_contrast")
        if t.get("warm_tone", 0.0) >= 0.48:
            add("romantic", "beach_warm")
        if (
            t.get("warm_tone", 0.0) >= WARM_ROMANTIC_MIN
            and t.get("saturation", 0.0) >= 0.40
            and t.get("brightness", 0.0) >= 0.40
        ):
            add("romantic", "beach_sunset_like")
        if t.get("saturation", 0.0) >= 0.55 and t.get("blue_tone", 0.0) >= 0.40:
            add("aesthetic", "beach_aesthetic")
        if _allow_calm(t) and t.get("warm_tone", 0.0) >= BEACH_COZY_WARM_MIN:
            cozy("beach_allow_calm_warm_cozy")

    elif category == "nature":
        if _allow_calm(t) and (
            (t.get("green_tone", 0.0) >= 0.22 or segment_vegetation >= 0.20)
            and t.get("saturation", 0.0) <= 0.55
            and t.get("contrast", 0.0) <= 0.45
        ):
            add("calm", "nature_calm_tone")
        if _allow_calm(t) and (
            t.get("saturation", 0.0) <= 0.52
            and t.get("contrast", 0.0) <= 0.48
            and (t.get("green_tone", 0.0) >= 0.18 or segment_vegetation >= 0.15)
        ):
            add("calm", "nature_low_sat_contrast")
        if t.get("contrast", 0.0) >= 0.50:
            add("energetic", "nature_contrast")
        if t.get("warm_tone", 0.0) >= 0.50 and t.get("brightness", 0.0) >= 0.45:
            add("romantic", "nature_warm_bright")
        if (
            t.get("green_tone", 0.0) >= NATURE_COZY_GREEN_MIN
            and t.get("warm_tone", 0.0) >= NATURE_COZY_WARM_MIN
            and t.get("contrast", 0.0) <= NATURE_COZY_CONTRAST_MAX
        ):
            cozy("nature_green_warm_cozy")

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
            and t.get("warm_tone", 0.0) >= WARM_ROMANTIC_MIN
        ):
            add("romantic", "culture_traditional_warm")
        if (
            subtype == "traditional_architecture"
            and t.get("warm_tone", 0.0) >= CULTURE_COZY_WARM_MIN
        ):
            cozy("culture_traditional_architecture_warm_cozy")
        if subtype == "historical_site" and t.get("warm_tone", 0.0) >= CULTURE_COZY_WARM_MIN:
            cozy("culture_historical_site_warm_cozy")
        if (
            subtype == "museum_gallery"
            and t.get("warm_tone", 0.0) >= WARM_COZY_MIN
            and _low_crowd(t)
        ):
            cozy("culture_museum_warm_quiet")

    elif category == "festival":
        crowd = float(fest.get("crowd_score", fest.get("crowd", 0.0)))
        vivid = float(fest.get("vivid_tone", fest.get("vivid_color", 0.0)))
        night = float(fest.get("night_lighting", 0.0))
        if crowd >= 0.30 or vivid >= 0.45:
            add("energetic", "festival_crowd_vivid")
        if night >= 0.35 or t.get("night_score", 0.0) >= 0.32:
            add("energetic", "festival_night")
            add("aesthetic", "festival_night")

    # Romantic: cafe + warm + low contrast (any category)
    if (
        "cafe" in tags
        and t.get("warm_tone", 0.0) >= WARM_ROMANTIC_MIN
        and t.get("contrast", 0.0) <= LOW_CONTRAST_ROMANTIC
    ):
        add("romantic", "cafe_warm_low_contrast")

    if calm_added and t.get("warm_tone", 0.0) >= 0.52:
        add("romantic", "calm_warm_combo")

    return _limit_style_hits(hits, max_styles=MAX_STYLE_LABELS)


def _tone_matches(style: str, t: Mapping[str, float]) -> bool:
    if style == "cozy":
        return t.get("warm_tone", 0.0) >= FOOD_COZY_WARM_MARKET
    if style == "calm":
        if t.get("person_ratio", 0.0) >= 0.12 or t.get("saturation", 0.0) >= 0.62:
            return False
        beach_calm = (
            t.get("brightness", 0.0) >= 0.50 and t.get("blue_tone", 0.0) >= 0.25
        ) or (
            t.get("saturation", 0.0) <= 0.52
            and t.get("contrast", 0.0) <= 0.48
            and t.get("blue_tone", 0.0) >= 0.20
        )
        nature_calm = (
            t.get("green_tone", 0.0) >= 0.18
            and t.get("saturation", 0.0) <= 0.55
            and t.get("contrast", 0.0) <= 0.48
        )
        return beach_calm or nature_calm
    if style == "romantic":
        return t.get("warm_tone", 0.0) >= 0.46
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
