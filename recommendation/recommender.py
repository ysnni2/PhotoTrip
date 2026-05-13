"""Top-k travel destination recommendations from a preference vector."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

_TOP_K = 3


def _get(pref: Mapping[str, float], key: str) -> float:
    return float(pref.get(key, 0.0))


def recommend(preference_vector: Mapping[str, float]) -> List[Dict[str, Any]]:
    """
    Score destinations from a preference vector and return the top 3 by score.
    """
    b = _get(preference_vector, "beach_affinity")
    n = _get(preference_vector, "nature_affinity")
    u = _get(preference_vector, "urban_affinity")
    ir = _get(preference_vector, "indoor_restaurant_affinity")
    im = _get(preference_vector, "indoor_museum_affinity")
    w = _get(preference_vector, "warm_tone")
    br = _get(preference_vector, "brightness")
    s = _get(preference_vector, "saturation")
    night = _get(preference_vector, "night_preference")

    cold = 1.0 - w

    destinations: Dict[str, float] = {
        "Bali": b * 0.5 + w * 0.3 + s * 0.2,
        "Maldives": b * 0.6 + w * 0.4,
        "Jeju": b * 0.4 + n * 0.4 + br * 0.2,
        "Swiss Alps": n * 0.6 + br * 0.2 + cold * 0.2,
        "Patagonia": n * 0.5 + cold * 0.3 + br * 0.2,
        "New Zealand": n * 0.5 + br * 0.3 + s * 0.2,
        "Tokyo": u * 0.4 + night * 0.4 + s * 0.2,
        "New York": u * 0.5 + night * 0.3 + br * 0.2,
        "Paris": u * 0.4 + im * 0.4 + w * 0.2,
        "Bangkok": ir * 0.5 + w * 0.3 + u * 0.2,
        "Rome": ir * 0.4 + im * 0.3 + w * 0.3,
        "Barcelona": ir * 0.4 + w * 0.3 + b * 0.3,
    }

    ranked = sorted(
        destinations.items(),
        key=lambda item: (-item[1], item[0]),
    )[:_TOP_K]

    return [
        {"rank": i + 1, "destination": name, "score": round(score, 2)}
        for i, (name, score) in enumerate(ranked)
    ]
