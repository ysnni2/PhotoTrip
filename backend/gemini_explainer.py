"""Generate Korean travel explanations via Google Gemini."""

from __future__ import annotations

import json
import os
from typing import Any, Mapping

from google import genai

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


def _generate(prompt: str) -> str:
    client = _get_client()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )
    text = (response.text or "").strip()
    if not text:
        raise ValueError("Gemini returned an empty response")
    return text


def explain(
    preference_vector: Mapping[str, Any],
    recommendation: Mapping[str, Any],
) -> str:
    """
    Build a 2–3 sentence Korean explanation of why the recommended destinations fit the user.
    """
    payload = {
        "preference_vector": preference_vector,
        "recommendation": recommendation,
    }
    prompt = f"""당신은 여행 추천 앱 PhotoTrip의 친근한 AI 가이드입니다.
아래 JSON은 사용자 사진 분석 결과(취향 벡터)와 추천 여행지입니다.

{json.dumps(payload, ensure_ascii=False, indent=2)}

위 데이터만 근거로, 추천된 여행지가 왜 어울리는지 **한국어 2~3문장**으로 설명하세요.
- 첫 문장: 핵심 취향 요약
- 이후: Top 추천지와 연결
- 존댓말, 밝고 따뜻한 톤
- JSON, 목록, 영어, 이모지 없이 본문만 출력"""

    try:
        return _generate(prompt)
    except Exception:
        top = recommendation.get("top_category", "")
        dests = recommendation.get("destinations", [])
        names = ", ".join(str(d) for d in dests[:3]) if dests else "추천 여행지"
        return (
            f"사진에서 {top} 취향이 두드러져요. "
            f"{names}처럼 그 분위기를 느낄 수 있는 곳을 골라봤어요. "
            "마음에 드는 도시를 골라 떠나보세요!"
        )


def random_explain() -> str:
    """
    Playful Korean message when recommendations are random (is_random=True).
    """
    prompt = """당신은 여행 추천 앱 PhotoTrip의 위트 있는 AI 가이드입니다.
사용자의 사진 취향이 뚜렷하지 않아 **랜덤 여행지**를 추천한 상황입니다.

아래 예시와 비슷한 느낌으로, **한국어 2문장** 짧은 멘트를 새로 작성하세요.
예시 톤: "당신은 정말 예측하기 어려운 매력을 가진 사람이군요! 비행기를 타고 랜덤으로 착륙해보는 건 어떨까요~?"

- 친근하고 유머러스하게
- 이모지 없이 본문만 출력"""

    try:
        return _generate(prompt)
    except Exception:
        return _RANDOM_FALLBACK
