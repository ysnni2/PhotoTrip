"""Top-k travel destination recommendations from a preference vector."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

_TOP_K = 3


def _get(pref: Mapping[str, float], key: str, *fallback_keys: str) -> float:
    v = pref.get(key)
    if v is not None:
        return float(v)
    for fk in fallback_keys:
        if fk in pref and pref[fk] is not None:
            return float(pref[fk])
    return 0.0


def recommend(preference_vector: Mapping[str, float]) -> List[Dict[str, Any]]:
    """
    Score destinations from the 7 theme signals (beach…food) plus tone / urban cues,
    then return the top 3 destinations by score.
    """
    beach = _get(preference_vector, "beach", "beach_affinity")
    nature = _get(preference_vector, "nature", "nature_affinity")
    city = _get(preference_vector, "city", "urban_affinity")
    if "indoor" in preference_vector:
        indoor = _get(preference_vector, "indoor")
    else:
        indoor = min(
            1.0,
            _get(preference_vector, "indoor_restaurant_affinity")
            + _get(preference_vector, "indoor_museum_affinity"),
        )
    culture = _get(preference_vector, "culture")
    fashion = _get(preference_vector, "fashion")
    food = _get(preference_vector, "food")

    w = _get(preference_vector, "warm_tone")
    br = _get(preference_vector, "brightness")
    s = _get(preference_vector, "saturation")
    night = _get(preference_vector, "night_preference")
    im = _get(preference_vector, "indoor_museum_affinity")

    cold = max(0.0, min(1.0, 1.0 - w))
    luxury = 0.5 * w + 0.5 * s

    def mix2(a: float, b: float) -> float:
        return 0.5 * a + 0.5 * b

    def mix3(a: float, b: float, c: float) -> float:
        return (a + b + c) / 3.0

    destinations: Dict[str, float] = {
        # beach
        "Bali": mix2(beach, w),
        "Maldives": mix2(beach, w),
        "Jeju": mix2(beach, nature),
        "Phuket": mix2(beach, w),
        # nature
        "Swiss Alps": mix2(nature, cold),
        "Patagonia": mix2(nature, cold),
        "New Zealand": mix2(nature, br),
        "Hokkaido": mix2(nature, cold),
        # city
        "Tokyo": mix2(city, night),
        "New York": mix2(city, br),
        "Singapore": mix2(city, w),
        "Hong Kong": mix2(city, night),
        # indoor
        "Paris cafe": mix2(indoor, w),
        "Melbourne": mix2(indoor, br),
        "Kyoto (indoor)": mix2(indoor, culture),
        "Amsterdam": mix2(indoor, br),
        # culture
        "Paris": mix2(culture, im),
        "Vatican": mix2(culture, im),
        "Kyoto (culture)": mix2(culture, nature),
        "Jerusalem": mix2(culture, night),
        # fashion
        "Milan": mix2(fashion, luxury),
        "Paris (fashion)": mix2(fashion, luxury),
        "Tokyo Harajuku": mix2(fashion, city),
        "Seoul Dongdaemun": mix2(fashion, city),
        "London": mix2(fashion, cold),
        # food
        "Tokyo (food)": mix2(food, city),
        "Bangkok": mix2(food, w),
        "Rome": mix2(food, w),
        "Taiwan": mix2(food, s),
        "New Orleans": mix3(food, br, s),
    }

    ranked = sorted(
        destinations.items(),
        key=lambda item: (-item[1], item[0]),
    )[:_TOP_K]

    return [
        {"rank": i + 1, "destination": name, "score": round(score, 2)}
        for i, (name, score) in enumerate(ranked)
    ]
