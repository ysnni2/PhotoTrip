"""CLIP-based lifestyle analyzers (place / mood / interest)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Mapping, Union
from pathlib import Path

from .interest_analyzer import INTEREST_LABELS, analyze_interest
from .mood_analyzer import MOOD_LABELS, analyze_mood
from .place_analyzer import PLACE_LABELS, analyze_place

__all__ = [
    "PLACE_LABELS",
    "MOOD_LABELS",
    "INTEREST_LABELS",
    "analyze_place",
    "analyze_mood",
    "analyze_interest",
    "analyze_lifestyle",
    "analyze_lifestyle_path",
    "save_lifestyle_csv",
]


def analyze_lifestyle(image: Any) -> dict:
    from .lifestyle_analyzer import analyze_lifestyle as _fn

    return _fn(image)


def analyze_lifestyle_path(input_path: Union[str, Path]) -> List[dict]:
    from .lifestyle_analyzer import analyze_lifestyle_path as _fn

    return _fn(input_path)


def save_lifestyle_csv(
    rows: Any,
    output_path: Union[str, Path] | None = None,
) -> Path:
    from .lifestyle_analyzer import save_lifestyle_csv as _fn

    if output_path is None:
        return _fn(rows)
    return _fn(rows, output_path)
