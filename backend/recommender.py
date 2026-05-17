"""Top-3 travel recommendations from a build_vector() preference vector."""

from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

SCENE_CATEGORIES = ("beach", "nature", "city", "culture", "festival", "food")

_TOP_K = 3
_UNCERTAIN_THRESHOLD = 0.3

_VISUAL_KEYS = ("brightness", "saturation", "contrast", "warm_tone")
_SEMANTIC_KEYS = (
    "water_ratio",
    "sky_ratio",
    "vegetation_ratio",
    "building_ratio",
    "food_ratio",
)


def _scene(**kwargs: float) -> Dict[str, float]:
    return {c: float(kwargs.get(c, 0.05)) for c in SCENE_CATEGORIES}


def _visual(
    brightness: float,
    saturation: float,
    contrast: float,
    warm_tone: float,
) -> Dict[str, float]:
    return {
        "brightness": brightness,
        "saturation": saturation,
        "contrast": contrast,
        "warm_tone": warm_tone,
    }


def _semantic(
    water: float = 0.0,
    sky: float = 0.0,
    vegetation: float = 0.0,
    building: float = 0.0,
    food: float = 0.0,
) -> Dict[str, float]:
    return {
        "water_ratio": water,
        "sky_ratio": sky,
        "vegetation_ratio": vegetation,
        "building_ratio": building,
        "food_ratio": food,
    }


# name, category, scene, visual, semantic
_DESTINATION_PROFILES: Tuple[Dict[str, Any], ...] = (
    # beach
    {
        "name": "발리",
        "category": "beach",
        "scene": _scene(beach=0.95, nature=0.15),
        "visual": _visual(0.78, 0.72, 0.45, 0.82),
        "semantic": _semantic(water=0.35, sky=0.25, vegetation=0.2),
    },
    {
        "name": "몰디브",
        "category": "beach",
        "scene": _scene(beach=0.98, nature=0.1),
        "visual": _visual(0.85, 0.68, 0.4, 0.75),
        "semantic": _semantic(water=0.55, sky=0.35, vegetation=0.05),
    },
    {
        "name": "제주",
        "category": "beach",
        "scene": _scene(beach=0.7, nature=0.55),
        "visual": _visual(0.72, 0.65, 0.5, 0.68),
        "semantic": _semantic(water=0.4, sky=0.3, vegetation=0.35),
    },
    {
        "name": "세부",
        "category": "beach",
        "scene": _scene(beach=0.92, food=0.1),
        "visual": _visual(0.8, 0.7, 0.42, 0.78),
        "semantic": _semantic(water=0.5, sky=0.28, vegetation=0.12),
    },
    {
        "name": "푸켓",
        "category": "beach",
        "scene": _scene(beach=0.93, food=0.12),
        "visual": _visual(0.82, 0.75, 0.44, 0.85),
        "semantic": _semantic(water=0.48, sky=0.26, vegetation=0.18),
    },
    # nature
    {
        "name": "뉴질랜드 퀸스타운",
        "category": "nature",
        "scene": _scene(nature=0.95, beach=0.08),
        "visual": _visual(0.75, 0.62, 0.55, 0.45),
        "semantic": _semantic(water=0.25, sky=0.35, vegetation=0.45),
    },
    {
        "name": "파타고니아",
        "category": "nature",
        "scene": _scene(nature=0.97),
        "visual": _visual(0.65, 0.5, 0.6, 0.25),
        "semantic": _semantic(sky=0.4, vegetation=0.35, water=0.15),
    },
    {
        "name": "설악산",
        "category": "nature",
        "scene": _scene(nature=0.9, culture=0.1),
        "visual": _visual(0.68, 0.55, 0.58, 0.4),
        "semantic": _semantic(vegetation=0.5, sky=0.35, water=0.1),
    },
    {
        "name": "요세미티",
        "category": "nature",
        "scene": _scene(nature=0.96),
        "visual": _visual(0.7, 0.58, 0.52, 0.42),
        "semantic": _semantic(vegetation=0.55, sky=0.3, water=0.12),
    },
    {
        "name": "아이슬란드",
        "category": "nature",
        "scene": _scene(nature=0.94, beach=0.12),
        "visual": _visual(0.62, 0.48, 0.55, 0.3),
        "semantic": _semantic(water=0.35, sky=0.4, vegetation=0.2),
    },
    # city
    {
        "name": "도쿄",
        "category": "city",
        "scene": _scene(city=0.95, festival=0.2, food=0.15),
        "visual": _visual(0.55, 0.7, 0.65, 0.45),
        "semantic": _semantic(building=0.55, sky=0.2, food=0.1),
    },
    {
        "name": "뉴욕",
        "category": "city",
        "scene": _scene(city=0.96, festival=0.25, culture=0.15),
        "visual": _visual(0.58, 0.68, 0.7, 0.4),
        "semantic": _semantic(building=0.6, sky=0.22, food=0.08),
    },
    {
        "name": "홍콩",
        "category": "city",
        "scene": _scene(city=0.94, food=0.2),
        "visual": _visual(0.52, 0.72, 0.68, 0.5),
        "semantic": _semantic(building=0.58, water=0.15, sky=0.18),
    },
    {
        "name": "싱가포르",
        "category": "city",
        "scene": _scene(city=0.9, food=0.25, beach=0.1),
        "visual": _visual(0.72, 0.75, 0.5, 0.62),
        "semantic": _semantic(building=0.5, water=0.2, vegetation=0.15),
    },
    {
        "name": "파리",
        "category": "city",
        "scene": _scene(city=0.85, culture=0.35, festival=0.3),
        "visual": _visual(0.6, 0.65, 0.55, 0.5),
        "semantic": _semantic(building=0.45, sky=0.25, food=0.1),
    },
    # culture
    {
        "name": "로마",
        "category": "culture",
        "scene": _scene(culture=0.95, city=0.25, food=0.2),
        "visual": _visual(0.72, 0.68, 0.5, 0.7),
        "semantic": _semantic(building=0.5, sky=0.2, food=0.15),
    },
    {
        "name": "교토",
        "category": "culture",
        "scene": _scene(culture=0.93, nature=0.3),
        "visual": _visual(0.65, 0.6, 0.48, 0.55),
        "semantic": _semantic(vegetation=0.4, building=0.35, sky=0.2),
    },
    {
        "name": "이스탄불",
        "category": "culture",
        "scene": _scene(culture=0.92, city=0.3, food=0.15),
        "visual": _visual(0.7, 0.65, 0.52, 0.72),
        "semantic": _semantic(building=0.45, water=0.2, sky=0.25),
    },
    {
        "name": "바르셀로나",
        "category": "culture",
        "scene": _scene(culture=0.9, beach=0.15, city=0.2),
        "visual": _visual(0.78, 0.72, 0.48, 0.75),
        "semantic": _semantic(building=0.4, water=0.18, sky=0.28),
    },
    {
        "name": "앙코르와트",
        "category": "culture",
        "scene": _scene(culture=0.97, nature=0.2),
        "visual": _visual(0.68, 0.58, 0.5, 0.6),
        "semantic": _semantic(vegetation=0.45, building=0.4, sky=0.25),
    },
    # festival
    {
        "name": "밀라노",
        "category": "festival",
        "scene": _scene(festival=0.95, city=0.3, culture=0.2),
        "visual": _visual(0.62, 0.78, 0.6, 0.55),
        "semantic": _semantic(building=0.45, sky=0.2),
    },
    {
        "name": "비엔나",
        "category": "festival",
        "scene": _scene(festival=0.9, culture=0.35),
        "visual": _visual(0.65, 0.7, 0.55, 0.5),
        "semantic": _semantic(building=0.5, sky=0.25, vegetation=0.15),
    },
    {
        "name": "리우데자네이루",
        "category": "festival",
        "scene": _scene(festival=0.88, beach=0.2, culture=0.15),
        "visual": _visual(0.75, 0.85, 0.55, 0.8),
        "semantic": _semantic(water=0.3, sky=0.25, building=0.2),
    },
    {
        "name": "에든버러",
        "category": "festival",
        "scene": _scene(festival=0.85, culture=0.3),
        "visual": _visual(0.55, 0.6, 0.62, 0.35),
        "semantic": _semantic(building=0.48, sky=0.35, vegetation=0.2),
    },
    {
        "name": "뉴욕 브로드웨이",
        "category": "festival",
        "scene": _scene(festival=0.92, city=0.5),
        "visual": _visual(0.5, 0.75, 0.72, 0.42),
        "semantic": _semantic(building=0.55, sky=0.15, food=0.08),
    },
    # food
    {
        "name": "나폴리",
        "category": "food",
        "scene": _scene(food=0.95, culture=0.25),
        "visual": _visual(0.75, 0.7, 0.48, 0.78),
        "semantic": _semantic(food=0.35, building=0.3, sky=0.2),
    },
    {
        "name": "방콕",
        "category": "food",
        "scene": _scene(food=0.92, city=0.25, culture=0.15),
        "visual": _visual(0.7, 0.8, 0.5, 0.75),
        "semantic": _semantic(food=0.3, building=0.35, water=0.12),
    },
    {
        "name": "오사카",
        "category": "food",
        "scene": _scene(food=0.93, city=0.3),
        "visual": _visual(0.68, 0.72, 0.55, 0.5),
        "semantic": _semantic(food=0.32, building=0.4, sky=0.15),
    },
    {
        "name": "멕시코시티",
        "category": "food",
        "scene": _scene(food=0.9, culture=0.2),
        "visual": _visual(0.72, 0.82, 0.52, 0.7),
        "semantic": _semantic(food=0.28, building=0.38, sky=0.22),
    },
    {
        "name": "이스탄불 (미식)",
        "category": "food",
        "scene": _scene(food=0.94, culture=0.35),
        "visual": _visual(0.7, 0.68, 0.5, 0.74),
        "semantic": _semantic(food=0.38, building=0.35, water=0.15),
    },
)


def _fix_semantic(semantic: Dict[str, float]) -> Dict[str, float]:
    """Normalize semantic dict to the five ratio keys (ignore extras like sand)."""
    return {k: float(semantic.get(k, 0.0)) for k in _SEMANTIC_KEYS}


def _flatten_vector(
    scene: Mapping[str, float],
    visual: Mapping[str, float],
    semantic: Mapping[str, float],
) -> np.ndarray:
    sem = _fix_semantic(semantic)
    parts = (
        [float(scene.get(c, 0.0)) for c in SCENE_CATEGORIES]
        + [float(visual.get(k, 0.0)) for k in _VISUAL_KEYS]
        + [sem[k] for k in _SEMANTIC_KEYS]
    )
    return np.asarray(parts, dtype=np.float64)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na < 1e-8 or nb < 1e-8:
        return 0.0
    return float(np.clip(np.dot(a, b) / (na * nb), 0.0, 1.0))


def _preference_to_array(preference_vector: Mapping[str, Any]) -> np.ndarray:
    return _flatten_vector(
        preference_vector.get("scene", {}),
        preference_vector.get("visual", {}),
        preference_vector.get("semantic", {}),
    )


def _all_scene_below_threshold(scene: Mapping[str, float], threshold: float) -> bool:
    if not scene:
        return True
    return max(float(v) for v in scene.values()) < threshold


def _categories_all_different(categories: Sequence[str]) -> bool:
    if len(categories) < 2:
        return False
    return len(set(categories)) == len(categories)


def _should_use_random(
    preference_vector: Mapping[str, Any],
    photo_top_categories: Optional[Sequence[str]] = None,
) -> bool:
    if bool(preference_vector.get("is_uncertain", False)):
        return True
    if float(preference_vector.get("confidence", 0.0)) < _UNCERTAIN_THRESHOLD:
        return True
    scene = preference_vector.get("scene", {})
    if isinstance(scene, Mapping) and _all_scene_below_threshold(scene, _UNCERTAIN_THRESHOLD):
        return True
    if photo_top_categories and _categories_all_different(photo_top_categories):
        return True
    return False


def _random_recommendation(
    preference_vector: Mapping[str, Any],
) -> Dict[str, Any]:
    names = [str(p["name"]) for p in _DESTINATION_PROFILES]
    k = min(_TOP_K, len(names))
    chosen = random.sample(names, k=k)
    scores = {name: round(random.uniform(0.5, 0.85), 2) for name in chosen}
    return {
        "destinations": chosen,
        "top_category": str(preference_vector.get("top_category", "")),
        "is_random": True,
        "scores": scores,
    }


def recommend(
    preference_vector: Mapping[str, Any],
    photo_top_categories: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """
  Recommend Top-3 destinations via cosine similarity to hand-crafted destination profiles.

  photo_top_categories: top_category from each photo in a session; if all differ, triggers random mode.
    """
    top_category = str(preference_vector.get("top_category", ""))

    if _should_use_random(preference_vector, photo_top_categories):
        return _random_recommendation(preference_vector)

    user_vec = _preference_to_array(preference_vector)
    ranked: List[Tuple[str, float]] = []

    for profile in _DESTINATION_PROFILES:
        dest_vec = _flatten_vector(
            profile["scene"],
            profile["visual"],
            _fix_semantic(profile["semantic"]),
        )
        score = _cosine_similarity(user_vec, dest_vec)
        ranked.append((str(profile["name"]), score))

    ranked.sort(key=lambda x: (-x[1], x[0]))
    top = ranked[:_TOP_K]

    return {
        "destinations": [name for name, _ in top],
        "top_category": top_category,
        "is_random": False,
        "scores": {name: round(score, 2) for name, score in top},
    }
