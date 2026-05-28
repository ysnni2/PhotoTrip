"""Gemini Vision travel-hint analysis for low-confidence (other) photos."""

from __future__ import annotations

from typing import Any, Dict, Optional

from PIL import Image

from gemini_explainer import (
    MODEL_NAME,
    _get_client,
    _log_gemini_error,
    _parse_json_object,
    _pil_to_jpeg_b64,
)

VALID_TRAVEL_HINTS = frozenset(
    {"city", "nature", "culture", "food", "beach", "festival"}
)

_DEFAULT_HINT: Dict[str, Any] = {
    "description": (
        "일상 속 작은 순간이지만, 어디론가 떠나고 싶은 마음이 느껴지는 사진이에요."
    ),
    "travel_hint": None,
    "hint_weight": 0.2,
    "mood_message": "분류는 애매하지만, 여행 욕구는 확실한 탑승권이에요.",
}


def _normalize_hint(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    hint = str(raw).strip().lower()
    if hint in ("null", "none", ""):
        return None
    return hint if hint in VALID_TRAVEL_HINTS else None


def _normalize_weight(raw: Any) -> float:
    try:
        w = float(raw)
    except (TypeError, ValueError):
        w = 0.3
    return round(max(0.1, min(0.5, w)), 2)


def analyze_other_as_travel_hint(image: Image.Image) -> Dict[str, Any]:
    """
    Low-confidence photo → travel-taste hint for preference_vector blending.

    Returns:
        description: friendly Korean travel-taste summary (1–2 sentences)
        travel_hint: city | nature | culture | food | beach | festival | None
        hint_weight: blend strength into scene scores (0.1–0.5)
        mood_message: one-line boarding-pass UI copy
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    prompt = """이 이미지는 여행 취향 분석 앱(PhotoTrip)에서 카테고리를 명확히 분류하지 못한 이미지입니다.
여행 취향 분석 관점에서 이 사진이 어떤 여행 스타일을 암시하는지 JSON으로만 답해줘.

규칙:
- description: 여행 취향 관점의 친근한 한국어 설명 1~2문장
- travel_hint: beach, nature, city, culture, food, festival 중 하나 또는 null
- hint_weight: 0.1~0.5 (애매할수록 낮게, 여행 연상이 뚜렷할수록 높게)
- mood_message: 가상 탑승권 UI에 쓸 짧고 재미있는 한 줄 한국어

JSON 형식만 출력:
{"description": "...", "travel_hint": "nature", "hint_weight": 0.3, "mood_message": "..."}"""

    try:
        client = _get_client()
    except Exception as exc:
        _log_gemini_error("analyze_other_as_travel_hint() client", exc)
        return dict(_DEFAULT_HINT)

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": _pil_to_jpeg_b64(image),
                            }
                        },
                    ],
                }
            ],
        )
        raw = _parse_json_object(response.text or "")
    except Exception as exc:
        _log_gemini_error("analyze_other_as_travel_hint() generate_content", exc)
        return dict(_DEFAULT_HINT)

    description = str(raw.get("description", "")).strip() or _DEFAULT_HINT["description"]
    mood_message = str(raw.get("mood_message", "")).strip() or _DEFAULT_HINT["mood_message"]

    return {
        "description": description,
        "travel_hint": _normalize_hint(raw.get("travel_hint")),
        "hint_weight": _normalize_weight(raw.get("hint_weight", 0.3)),
        "mood_message": mood_message,
    }
