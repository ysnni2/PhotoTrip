"""Refined style pseudo-label rules (hard / weak / discard).

Primary ``refined_style_label`` comes from core styles only (calm, energetic, local, aesthetic).
Cozy / romantic rules augment ``style_multihot`` and ``style_candidates`` for MLP training.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from .labels import STYLE_LABELS

CATEGORY_CONF_HARD = 0.55
CATEGORY_CONF_WEAK = 0.38
CATEGORY_CONF_DISCARD = 0.32
MAX_PRIMARY_CANDIDATES = 2
MAX_MULTIHOT_LABELS = 5

PRIMARY_STYLES = frozenset({"calm", "energetic", "local", "aesthetic"})
SUPPLEMENT_STYLES = frozenset({"cozy", "romantic"})

WARM_COZY_MIN = 0.42
FOOD_COZY_WARM_STRONG = 0.60
TAG_CAFE_COZY_WARM_MIN = 0.50
FOOD_COZY_WARM_CAFE = 0.50
FOOD_COZY_WARM_MARKET = 0.48
NATURE_COZY_GREEN_MIN = 0.20
NATURE_COZY_WARM_MIN = 0.48
NATURE_COZY_CONTRAST_MAX = 0.40
BEACH_COZY_WARM_MIN = 0.55
BEACH_COZY_CONTRAST_MAX = 0.40
CULTURE_COZY_WARM_MIN = 0.48
WARM_ROMANTIC_MIN = 0.46
LOW_CONTRAST_COZY = 0.48
LOW_CONTRAST_ROMANTIC = 0.46


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


def _has_cozy_anchor(
    *,
    category: str,
    culture_subtype: Optional[str],
    tags: Set[str],
    t: Mapping[str, float],
    visual_tone: Mapping[str, float],
) -> bool:
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
    return False


def _allow_calm(t: Mapping[str, float]) -> bool:
    if t.get("person_ratio", 0.0) >= 0.12:
        return False
    if t.get("saturation", 0.0) >= 0.62:
        return False
    return True


def _low_crowd(t: Mapping[str, float]) -> bool:
    return t.get("person_ratio", 0.0) < 0.12


def _limit_primary_hits(
    hits: List[Tuple[str, str]],
    *,
    max_styles: int = MAX_PRIMARY_CANDIDATES,
) -> List[Tuple[str, str]]:
    if not hits:
        return hits
    counts: Dict[str, int] = defaultdict(int)
    for style, _ in hits:
        counts[style] += 1
    allowed = set(
        sorted(counts.keys(), key=lambda s: (-counts[s], s))[:max_styles]
    )
    return [(s, r) for s, r in hits if s in allowed]


def collect_style_rule_hits(
    *,
    category: str,
    culture_subtype: Optional[str],
    interest_tags: Sequence[Mapping[str, Any]],
    visual_tone: Mapping[str, float],
    festival_evidence: Optional[Mapping[str, float]] = None,
    segment_vegetation: float = 0.0,
) -> Dict[str, List[Tuple[str, str]]]:
    """Return ``primary`` and ``supplement`` (cozy/romantic) rule hit lists."""
    tags = _tags(interest_tags)
    t = _tone(visual_tone)
    fest = festival_evidence or {}
    subtype = culture_subtype or ""
    primary: List[Tuple[str, str]] = []
    supplement: List[Tuple[str, str]] = []
    calm_added = False

    def add(style: str, rule: str) -> None:
        primary.append((style, rule))
        nonlocal calm_added
        if style == "calm":
            calm_added = True

    def cozy(rule: str) -> None:
        if _has_cozy_anchor(
            category=category,
            culture_subtype=subtype or None,
            tags=tags,
            t=t,
            visual_tone=visual_tone,
        ):
            supplement.append(("cozy", rule))

    def romantic(rule: str) -> None:
        supplement.append(("romantic", rule))

    if "history" in tags:
        add("local", "tag_history")

    if category in ("festival", "city"):
        if "nightlife" in tags:
            add("energetic", "tag_nightlife")
        if "sports" in tags:
            add("energetic", "tag_sports")

    if category == "food":
        if "cafe" in tags and t.get("warm_tone", 0.0) >= FOOD_COZY_WARM_CAFE:
            cozy("food_cafe_warm_cozy")
        if t.get("warm_tone", 0.0) >= FOOD_COZY_WARM_STRONG:
            cozy("food_warm_strong_cozy")
        if "local_market" in tags and t.get("warm_tone", 0.0) >= FOOD_COZY_WARM_MARKET:
            cozy("food_local_market_warm_cozy")
        if (
            "cafe" in tags
            and t.get("warm_tone", 0.0) >= 0.55
            and t.get("contrast", 0.0) <= 0.45
        ):
            add("aesthetic", "food_cafe_aesthetic")
        if "cafe" in tags and t.get("warm_tone", 0.0) >= 0.50:
            romantic("food_cafe_romantic")
        if "local_market" in tags:
            add("local", "food_local_market")
            add("energetic", "food_local_market")

    if "cafe" in tags and t.get("warm_tone", 0.0) >= TAG_CAFE_COZY_WARM_MIN:
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
            romantic("city_night_warm")
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
            romantic("beach_warm")
        if (
            t.get("warm_tone", 0.0) >= WARM_ROMANTIC_MIN
            and t.get("saturation", 0.0) >= 0.40
            and t.get("brightness", 0.0) >= 0.40
        ):
            romantic("beach_sunset_like")
        if t.get("saturation", 0.0) >= 0.55 and t.get("blue_tone", 0.0) >= 0.40:
            add("aesthetic", "beach_aesthetic")
        if (
            _allow_calm(t)
            and t.get("warm_tone", 0.0) >= BEACH_COZY_WARM_MIN
            and t.get("contrast", 0.0) <= BEACH_COZY_CONTRAST_MAX
        ):
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
            romantic("nature_warm_bright")
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
            romantic("culture_traditional_warm")
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

    if (
        "cafe" in tags
        and t.get("warm_tone", 0.0) >= WARM_ROMANTIC_MIN
        and t.get("contrast", 0.0) <= LOW_CONTRAST_ROMANTIC
    ):
        romantic("cafe_warm_low_contrast")

    if calm_added and t.get("warm_tone", 0.0) >= 0.52:
        romantic("calm_warm_combo")

    primary = _limit_primary_hits(primary, max_styles=MAX_PRIMARY_CANDIDATES)
    return {"primary": primary, "supplement": supplement}


def collect_style_rule_hits_flat(**kwargs: Any) -> List[Tuple[str, str]]:
    """Flat list of all hits (primary + supplement) for backward compatibility."""
    split = collect_style_rule_hits(**kwargs)
    return split["primary"] + split["supplement"]


def _tone_matches(style: str, t: Mapping[str, float]) -> bool:
    if style in SUPPLEMENT_STYLES:
        return True
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
    if style == "energetic":
        return (
            t.get("contrast", 0.0) >= 0.38
            or t.get("night_score", 0.0) >= 0.28
            or t.get("saturation", 0.0) >= 0.42
        )
    if style == "aesthetic":
        return t.get("contrast", 0.0) >= 0.32 or t.get("saturation", 0.0) >= 0.38
    return True


def _build_multihot_and_candidates(
    *,
    primary_style: Optional[str],
    primary_ranked: List[str],
    supplement_styles: List[str],
) -> Tuple[Dict[str, float], List[str]]:
    multihot = {s: 0.0 for s in STYLE_LABELS}
    candidates: List[str] = []

    if primary_style:
        multihot[primary_style] = 1.0
        candidates.append(primary_style)

    for style in primary_ranked:
        if style != primary_style and style not in candidates:
            candidates.append(style)
        multihot[style] = 1.0

    for style in supplement_styles:
        multihot[style] = 1.0
        if style not in candidates:
            candidates.append(style)

    candidates = candidates[:MAX_MULTIHOT_LABELS]
    active = sum(1 for v in multihot.values() if v >= 0.5)
    if active > MAX_MULTIHOT_LABELS:
        keep = set(candidates)
        for s in STYLE_LABELS:
            if s not in keep:
                multihot[s] = 0.0
    return multihot, candidates


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
    split = collect_style_rule_hits(
        category=category,
        culture_subtype=culture_subtype,
        interest_tags=interest_tags,
        visual_tone=visual_tone,
        festival_evidence=festival_evidence,
        segment_vegetation=segment_vegetation,
    )
    primary_hits = split["primary"]
    supplement_hits = split["supplement"]
    all_hits = primary_hits + supplement_hits

    primary_rules: Dict[str, List[str]] = defaultdict(list)
    for style, rule in primary_hits:
        primary_rules[style].append(rule)

    supplement_rules: Dict[str, List[str]] = defaultdict(list)
    for style, rule in supplement_hits:
        supplement_rules[style].append(rule)

    rule_hits_payload = [
        {"style": s, "rule": r, "tier": "primary"} for s, r in primary_hits
    ] + [
        {"style": s, "rule": r, "tier": "supplement"} for s, r in supplement_hits
    ]

    if category_confidence < CATEGORY_CONF_DISCARD or not primary_hits:
        supplement_only = bool(supplement_hits)
        multihot, candidates = _build_multihot_and_candidates(
            primary_style=None,
            primary_ranked=[],
            supplement_styles=sorted(supplement_rules.keys()),
        )
        return {
            "refined_style_label": None,
            "style_candidates": candidates,
            "style_multihot": multihot,
            "label_status": "weak" if supplement_only else "discard",
            "discard_reason": None if supplement_only else "low_confidence_or_no_primary_rules",
            "rule_hits": rule_hits_payload,
            "primary_rule_hits": [{"style": s, "rule": r} for s, r in primary_hits],
            "supplement_rule_hits": [{"style": s, "rule": r} for s, r in supplement_hits],
        }

    ranked = sorted(
        ((s, len(r)) for s, r in primary_rules.items()),
        key=lambda x: (-x[1], x[0]),
    )
    primary, evidence_count = ranked[0]
    primary_ranked = [s for s, _ in ranked[:MAX_PRIMARY_CANDIDATES]]
    supplement_styles = sorted(supplement_rules.keys())
    tone_ok = _tone_matches(primary, _tone(visual_tone))

    multihot, candidates = _build_multihot_and_candidates(
        primary_style=primary,
        primary_ranked=primary_ranked,
        supplement_styles=supplement_styles,
    )

    status = "discard"
    reason: Optional[str] = None

    if evidence_count >= 2 and category_confidence >= CATEGORY_CONF_HARD and tone_ok:
        status = "hard"
    elif evidence_count >= 1 and category_confidence >= CATEGORY_CONF_WEAK:
        status = "weak"
        if evidence_count < 2:
            reason = "single_primary_rule"
        elif not tone_ok:
            reason = "tone_mismatch"
        elif category_confidence < CATEGORY_CONF_HARD:
            reason = "category_conf_not_hard"
    else:
        reason = "ambiguous_primary_rules"
        primary = None
        multihot, candidates = _build_multihot_and_candidates(
            primary_style=None,
            primary_ranked=[],
            supplement_styles=supplement_styles,
        )

    calm_count = len(primary_rules.get("calm", []))
    if (
        primary == "calm"
        and len(primary_rules) > 1
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
        "rule_hits": rule_hits_payload,
        "primary_rule_hits": [{"style": s, "rule": r} for s, r in primary_hits],
        "supplement_rule_hits": [{"style": s, "rule": r} for s, r in supplement_hits],
        "style_rule_counts": {
            **{s: len(rs) for s, rs in primary_rules.items()},
            **{f"{s}_supplement": len(rs) for s, rs in supplement_rules.items()},
        },
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
