"""Shared label vocabularies for PhotoTrip analyzers and MLP training."""

from __future__ import annotations

PLACE_LABELS = ["beach", "nature", "city", "food", "festival", "culture"]

MOOD_LABELS = ["calm", "cozy", "romantic", "energetic", "local", "aesthetic"]

STYLE_LABELS = list(MOOD_LABELS)

INTEREST_TAG_LABELS = [
    "anime",
    "disney_themepark",
    "sports",
    "cafe",
    "shopping",
    "nightlife",
    "art",
    "history",
    "local_market",
]

CULTURE_SUBTYPE_LABELS = [
    "museum_gallery",
    "historical_site",
    "traditional_architecture",
    "modern_architecture",
    "pop_culture",
    "exhibition_performance",
]

FESTIVAL_SUBTYPE_LABELS = [
    "concert",
    "festival",
    "carnival",
    "sports_event",
    "nightlife_event",
    "parade",
    "not_festival",
]
