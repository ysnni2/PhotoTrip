"""Generate Korean travel explanations via Google Gemini."""

from __future__ import annotations

import base64
import io
import json
import os
import re
import traceback
from typing import Any, Dict, Mapping

from google import genai
from PIL import Image

MODEL_NAME = "gemini-2.5-flash"

_client: genai.Client | None = None

_RANDOM_FALLBACK = (
    "당신은 정말 예측하기 어려운 매력을 가진 사람이군요! "
    "비행기를 타고 랜덤으로 착륙해보는 건 어떨까요~?"
)


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY environment variable is not set")
        _client = genai.Client(api_key=api_key)
    return _client


def _log_gemini_error(context: str, exc: Exception) -> None:
    print(f"[Gemini 오류] {context} | {type(exc).__name__}: {exc}")
    traceback.print_exc()


def _generate(prompt: str) -> str:
    try:
        client = _get_client()
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )
        text = (response.text or "").strip()
        if not text:
            raise ValueError("Gemini returned an empty response")
        return text
    except Exception as e:
        _log_gemini_error("_generate()", e)
        raise


def explain(
    preference_vector: Mapping[str, Any],
    recommendation: Mapping[str, Any],
) -> str:
    """
    Build a structured Korean CV analysis report for the recommended destinations.
    """
    payload = {
        "preference_vector": preference_vector,
        "recommendation": recommendation,
    }
    analysis_json = json.dumps(payload, ensure_ascii=False, indent=2)
    prompt = f"""당신은 여행 큐레이터입니다.
아래 CV 분석 결과를 바탕으로 사용자의 여행 스타일을 설명해주세요.

아래 문구는 절대 출력하지 말 것:
- "차분하고 세련된"
- "감성적인 분이시네요"
- "여유로운 시간을"
- "특별한 추억을"

대신 preference_vector 안의 실제 수치를 언급할 것:
- scene.food가 높으면 → "음식 사진 비중이 높게 나왔어요!"
- warm_tone이 높으면 → "따뜻한 색감의 사진을 많이 찍으시네요"
- brightness가 높으면 → "밝고 화사한 사진을 좋아하시는군요"
visual, semantic, scene, style 수치도 필요하면 활용할 것.

top_category별 말투 (recommendation.top_category 기준, 아래 톤에 맞게):
- food: "먹는 게 여행이다! 현지 맛집 탐방 스타일이시네요 🍜"
- city: "도시의 에너지를 즐기시는 분! 야경 보며 걷고 싶으시죠? 🌆"
- beach: "파도 소리가 그리우신가요? 바다가 부르고 있어요! 🌊"
- nature: "도시 소음에서 벗어나 자연이 그리우신 분이군요 🌿"
- culture: "진짜 그 나라를 느끼고 싶은 탐구형 여행자시네요 🏛️"
- festival: "흥이 넘치는 분! 축제 현장에서 같이 뛰고 싶으시죠? 🎉"

2~3문장, 자연스러운 존댓말.
** 같은 마크다운 기호 사용 금지
추천 여행지(recommendation.destinations)가 왜 어울리는지 한 문장 포함.

분석 데이터: {analysis_json}

위 분석 데이터만 참고하여, top_category에 맞는 톤으로 본문만 출력하세요."""

    try:
        return _generate(prompt)
    except Exception as e:
        _log_gemini_error("explain()", e)
        dests = recommendation.get("destinations", [])
        dest = str(dests[0]) if dests else "추천 여행지"
        return (
            "차분하고 세련된 감성을 가진 분이시네요. "
            "사진에서 느껴지는 분위기와 어울리는 여행지를 골라봤어요. "
            f"{dest}에서 특별한 시간을 내보시는 건 어떨까요?"
        )


def _pil_to_jpeg_b64(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=88)
    return base64.standard_b64encode(buf.getvalue()).decode("ascii")


def _parse_json_object(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def classify_festival_subtype(
    image: Image.Image,
    festival_evidence: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Gemini Vision festival subtype with OpenCV evidence context."""
    empty = {
        "festival_subtype": "not_festival",
        "festival_confidence": 0.0,
        "gemini_fallback_used": False,
    }
    try:
        client = _get_client()
    except Exception as e:
        _log_gemini_error("classify_festival_subtype() client", e)
        return empty

    prompt = f"""Classify this photo's event atmosphere.
OpenCV evidence JSON:
{json.dumps(dict(festival_evidence or {}), ensure_ascii=False)}

Return JSON only:
{{"festival_subtype": "festival", "festival_confidence": 0.7}}

Labels: concert, festival, carnival, sports_event, nightlife_event, parade, not_festival"""

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
        subtype = str(raw.get("festival_subtype", "not_festival"))
        conf = round(min(1.0, max(0.0, float(raw.get("festival_confidence", 0.0)))), 4)
        return {
            "festival_subtype": subtype,
            "festival_confidence": conf,
            "gemini_fallback_used": True,
        }
    except Exception as e:
        _log_gemini_error("classify_festival_subtype() generate_content", e)
        return empty


def random_explain(reason: str = "uncertain") -> str:
    """
    Playful Korean message when recommendations are random (is_random=True).
    """
    if reason == "homebody":
        prompt = """당신은 PhotoTrip AI 가이드입니다. 사용자가 주로 실내(소파, 침대, 음식 등) 사진을 올린 집순이입니다.
집순이 캐릭터를 인정하면서도 여행을 부드럽게 권유하는 한국어 2문장을 작성하세요.
이모지 없이 본문만 출력."""
        fallback = (
            "집에서 쉬는 것도 좋지만, 가끔은 낯선 곳에서 새로운 에너지를 충전해보세요."
        )
    elif reason == "unpredictable":
        prompt = """당신은 PhotoTrip AI 가이드입니다. 사용자 취향이 너무 다양해서 예측이 불가능했고 랜덤 추천을 했습니다.
'예측할 수 없는 탑승권' 컨셉으로, 운명적인 여행의 설렘을 표현하는 한국어 2문장을 작성하세요.
이모지 없이 본문만 출력."""
        fallback = (
            "예측할 수 없는 탑승권이 발급되었습니다. 운명이 정한 여행지로 떠나볼까요?"
        )
    else:
        prompt = """당신은 여행 추천 앱 PhotoTrip의 위트 있는 AI 가이드입니다.
사용자의 사진 취향이 뚜렷하지 않아 **랜덤 여행지**를 추천한 상황입니다.

아래 예시와 비슷한 느낌으로, **한국어 2문장** 짧은 멘트를 새로 작성하세요.
예시 톤: "당신은 정말 예측하기 어려운 매력을 가진 사람이군요! 비행기를 타고 랜덤으로 착륙해보는 건 어떨까요~?"

- 친근하고 유머러스하게
- 이모지 없이 본문만 출력"""
        fallback = _RANDOM_FALLBACK

    try:
        return _generate(prompt)
    except Exception as e:
        _log_gemini_error(f"random_explain(reason={reason!r})", e)
        return fallback
