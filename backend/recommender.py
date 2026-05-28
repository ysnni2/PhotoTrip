"""Top-3 travel recommendations from a build_vector() preference vector."""

from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

SCENE_CATEGORIES = ("beach", "nature", "city", "culture", "festival", "food")

_TOP_K = 3
_MIN_DESTINATIONS = 3
_MAX_DESTINATIONS = 5
_UNCERTAIN_THRESHOLD = 0.3
_INTEREST_MATCH_BONUS = 0.05
_INTEREST_BONUS_MAX = 0.20
_HOMEBODY_KEYWORDS = {
    "sofa", "bed", "chair", "table", "desk", "monitor",
    "cabinet", "shelf", "lamp", "curtain", "carpet",
}
_HOMEBODY_MESSAGES = [
    "집순이 발견! 그래도 가끔은 나가봐요~",
    "집이 제일 좋죠? 그래도 여행지 하나 추천해드릴게요!",
    "완벽한 집순이 감지! 용기내서 떠나봐요!",
]
_UNPREDICTABLE_MESSAGES = [
    "예측할 수 없는 탑승권이 발급되었습니다. 운명의 여행지로 떠나볼까요?",
    "당신의 취향은 너무 다채로워요! 운명이 세 곳을 대신 골랐습니다.",
    "다양한 매력의 소유자! 어디든 잘 맞을 것 같아 랜덤으로 골라봤어요.",
]

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


# name, category, scene, visual, semantic, interest_tags
_DESTINATION_PROFILES: Tuple[Dict[str, Any], ...] = (
    # beach
    {
        "name": "발리",
        "category": "beach",
        "scene": _scene(beach=0.95, nature=0.15),
        "visual": _visual(0.78, 0.72, 0.45, 0.82),
        "semantic": _semantic(water=0.35, sky=0.25, vegetation=0.2),
        "interest_tags": ["cafe", "nature"],
    },
    {
        "name": "몰디브",
        "category": "beach",
        "scene": _scene(beach=0.98, nature=0.1),
        "visual": _visual(0.85, 0.68, 0.4, 0.75),
        "semantic": _semantic(water=0.55, sky=0.35, vegetation=0.05),
        "interest_tags": ["nature", "cafe"],
    },
    {
        "name": "제주",
        "category": "beach",
        "scene": _scene(beach=0.7, nature=0.55),
        "visual": _visual(0.72, 0.65, 0.5, 0.68),
        "semantic": _semantic(water=0.4, sky=0.3, vegetation=0.35),
        "interest_tags": ["nature", "cafe", "local_market"],
    },
    {
        "name": "세부",
        "category": "beach",
        "scene": _scene(beach=0.92, food=0.1),
        "visual": _visual(0.8, 0.7, 0.42, 0.78),
        "semantic": _semantic(water=0.5, sky=0.28, vegetation=0.12),
        "interest_tags": ["street_food", "local_market", "nightlife"],
    },
    {
        "name": "푸켓",
        "category": "beach",
        "scene": _scene(beach=0.93, food=0.12),
        "visual": _visual(0.82, 0.75, 0.44, 0.85),
        "semantic": _semantic(water=0.48, sky=0.26, vegetation=0.18),
        "interest_tags": ["street_food", "nightlife", "local_market"],
    },
    # nature
    {
        "name": "뉴질랜드 퀸스타운",
        "category": "nature",
        "scene": _scene(nature=0.95, beach=0.08),
        "visual": _visual(0.75, 0.62, 0.55, 0.45),
        "semantic": _semantic(water=0.25, sky=0.35, vegetation=0.45),
        "interest_tags": ["sports", "nature"],
    },
    {
        "name": "파타고니아",
        "category": "nature",
        "scene": _scene(nature=0.97),
        "visual": _visual(0.65, 0.5, 0.6, 0.25),
        "semantic": _semantic(sky=0.4, vegetation=0.35, water=0.15),
        "interest_tags": ["nature", "sports"],
    },
    {
        "name": "설악산",
        "category": "nature",
        "scene": _scene(nature=0.9, culture=0.1),
        "visual": _visual(0.68, 0.55, 0.58, 0.4),
        "semantic": _semantic(vegetation=0.5, sky=0.35, water=0.1),
        "interest_tags": ["nature", "history"],
    },
    {
        "name": "요세미티",
        "category": "nature",
        "scene": _scene(nature=0.96),
        "visual": _visual(0.7, 0.58, 0.52, 0.42),
        "semantic": _semantic(vegetation=0.55, sky=0.3, water=0.12),
        "interest_tags": ["nature", "sports"],
    },
    {
        "name": "아이슬란드",
        "category": "nature",
        "scene": _scene(nature=0.94, beach=0.12),
        "visual": _visual(0.62, 0.48, 0.55, 0.3),
        "semantic": _semantic(water=0.35, sky=0.4, vegetation=0.2),
        "interest_tags": ["nature", "art"],
    },
    # city
    {
        "name": "도쿄",
        "category": "city",
        "scene": _scene(city=0.95, festival=0.2, food=0.15),
        "visual": _visual(0.55, 0.7, 0.65, 0.45),
        "semantic": _semantic(building=0.55, sky=0.2, food=0.1),
        "interest_tags": ["shopping", "nightlife", "cafe", "anime"],
    },
    {
        "name": "뉴욕",
        "category": "city",
        "scene": _scene(city=0.96, festival=0.25, culture=0.15),
        "visual": _visual(0.58, 0.68, 0.7, 0.4),
        "semantic": _semantic(building=0.6, sky=0.22, food=0.08),
        "interest_tags": ["shopping", "nightlife", "art"],
    },
    {
        "name": "홍콩",
        "category": "city",
        "scene": _scene(city=0.94, food=0.2),
        "visual": _visual(0.52, 0.72, 0.68, 0.5),
        "semantic": _semantic(building=0.58, water=0.15, sky=0.18),
        "interest_tags": ["shopping", "nightlife", "street_food"],
    },
    {
        "name": "싱가포르",
        "category": "city",
        "scene": _scene(city=0.9, food=0.25, beach=0.1),
        "visual": _visual(0.72, 0.75, 0.5, 0.62),
        "semantic": _semantic(building=0.5, water=0.2, vegetation=0.15),
        "interest_tags": ["shopping", "cafe", "street_food"],
    },
    {
        "name": "파리",
        "category": "city",
        "scene": _scene(city=0.85, culture=0.35, festival=0.3),
        "visual": _visual(0.6, 0.65, 0.55, 0.5),
        "semantic": _semantic(building=0.45, sky=0.25, food=0.1),
        "interest_tags": ["cafe", "art", "shopping"],
    },
    # culture
    {
        "name": "로마",
        "category": "culture",
        "scene": _scene(culture=0.95, city=0.25, food=0.2),
        "visual": _visual(0.72, 0.68, 0.5, 0.7),
        "semantic": _semantic(building=0.5, sky=0.2, food=0.15),
        "interest_tags": ["history", "art", "local_market"],
    },
    {
        "name": "교토",
        "category": "culture",
        "scene": _scene(culture=0.93, nature=0.3),
        "visual": _visual(0.65, 0.6, 0.48, 0.55),
        "semantic": _semantic(vegetation=0.4, building=0.35, sky=0.2),
        "interest_tags": ["cafe", "history", "local_market"],
    },
    {
        "name": "이스탄불",
        "category": "culture",
        "scene": _scene(culture=0.92, city=0.3, food=0.15),
        "visual": _visual(0.7, 0.65, 0.52, 0.72),
        "semantic": _semantic(building=0.45, water=0.2, sky=0.25),
        "interest_tags": ["history", "local_market", "street_food"],
    },
    {
        "name": "바르셀로나",
        "category": "culture",
        "scene": _scene(culture=0.9, beach=0.15, city=0.2),
        "visual": _visual(0.78, 0.72, 0.48, 0.75),
        "semantic": _semantic(building=0.4, water=0.18, sky=0.28),
        "interest_tags": ["cafe", "art", "shopping"],
    },
    {
        "name": "앙코르와트",
        "category": "culture",
        "scene": _scene(culture=0.97, nature=0.2),
        "visual": _visual(0.68, 0.58, 0.5, 0.6),
        "semantic": _semantic(vegetation=0.45, building=0.4, sky=0.25),
        "interest_tags": ["history", "art"],
    },
    # festival
    {
        "name": "밀라노",
        "category": "festival",
        "scene": _scene(festival=0.95, city=0.3, culture=0.2),
        "visual": _visual(0.62, 0.78, 0.6, 0.55),
        "semantic": _semantic(building=0.45, sky=0.2),
        "interest_tags": ["shopping", "art", "cafe"],
    },
    {
        "name": "비엔나",
        "category": "festival",
        "scene": _scene(festival=0.9, culture=0.35),
        "visual": _visual(0.65, 0.7, 0.55, 0.5),
        "semantic": _semantic(building=0.5, sky=0.25, vegetation=0.15),
        "interest_tags": ["art", "history", "cafe"],
    },
    {
        "name": "리우데자네이루",
        "category": "festival",
        "scene": _scene(festival=0.88, beach=0.2, culture=0.15),
        "visual": _visual(0.75, 0.85, 0.55, 0.8),
        "semantic": _semantic(water=0.3, sky=0.25, building=0.2),
        "interest_tags": ["nightlife", "street_food", "sports"],
    },
    {
        "name": "에든버러",
        "category": "festival",
        "scene": _scene(festival=0.85, culture=0.3),
        "visual": _visual(0.55, 0.6, 0.62, 0.35),
        "semantic": _semantic(building=0.48, sky=0.35, vegetation=0.2),
        "interest_tags": ["history", "art", "nightlife"],
    },
    {
        "name": "뉴욕 브로드웨이",
        "category": "festival",
        "scene": _scene(festival=0.92, city=0.5),
        "visual": _visual(0.5, 0.75, 0.72, 0.42),
        "semantic": _semantic(building=0.55, sky=0.15, food=0.08),
        "interest_tags": ["nightlife", "art", "shopping"],
    },
    # food
    {
        "name": "나폴리",
        "category": "food",
        "scene": _scene(food=0.95, culture=0.25),
        "visual": _visual(0.75, 0.7, 0.48, 0.78),
        "semantic": _semantic(food=0.35, building=0.3, sky=0.2),
        "interest_tags": ["street_food", "history", "local_market"],
    },
    {
        "name": "방콕",
        "category": "food",
        "scene": _scene(food=0.92, city=0.25, culture=0.15),
        "visual": _visual(0.7, 0.8, 0.5, 0.75),
        "semantic": _semantic(food=0.3, building=0.35, water=0.12),
        "interest_tags": ["street_food", "local_market", "nightlife"],
    },
    {
        "name": "오사카",
        "category": "food",
        "scene": _scene(food=0.93, city=0.3),
        "visual": _visual(0.68, 0.72, 0.55, 0.5),
        "semantic": _semantic(food=0.32, building=0.4, sky=0.15),
        "interest_tags": ["local_market", "street_food", "cafe"],
    },
    {
        "name": "멕시코시티",
        "category": "food",
        "scene": _scene(food=0.9, culture=0.2),
        "visual": _visual(0.72, 0.82, 0.52, 0.7),
        "semantic": _semantic(food=0.28, building=0.38, sky=0.22),
        "interest_tags": ["street_food", "local_market", "history"],
    },
    {
        "name": "이스탄불 (미식)",
        "category": "food",
        "scene": _scene(food=0.94, culture=0.35),
        "visual": _visual(0.7, 0.68, 0.5, 0.74),
        "semantic": _semantic(food=0.38, building=0.35, water=0.15),
        "interest_tags": ["street_food", "history", "local_market"],
    },
    # beach (expanded)
    {
        "name": "세이셸",
        "category": "beach",
        "scene": _scene(beach=0.96, nature=0.12),
        "visual": _visual(0.88, 0.7, 0.38, 0.8),
        "semantic": _semantic(water=0.52, sky=0.3, vegetation=0.1),
        "interest_tags": ["nature", "cafe"],
    },
    {
        "name": "필리핀 팔라완",
        "category": "beach",
        "scene": _scene(beach=0.94, nature=0.2),
        "visual": _visual(0.8, 0.72, 0.42, 0.82),
        "semantic": _semantic(water=0.5, sky=0.28, vegetation=0.22),
        "interest_tags": ["nature", "street_food"],
    },
    {
        "name": "산토리니",
        "category": "beach",
        "scene": _scene(beach=0.9, culture=0.25),
        "visual": _visual(0.85, 0.75, 0.45, 0.78),
        "semantic": _semantic(water=0.45, sky=0.32, building=0.15),
        "interest_tags": ["cafe", "art", "history"],
    },
    {
        "name": "두브로브니크",
        "category": "beach",
        "scene": _scene(beach=0.88, culture=0.3),
        "visual": _visual(0.78, 0.68, 0.5, 0.65),
        "semantic": _semantic(water=0.42, building=0.35, sky=0.25),
        "interest_tags": ["history", "cafe", "art"],
    },
    {
        "name": "골드코스트",
        "category": "beach",
        "scene": _scene(beach=0.93, city=0.12),
        "visual": _visual(0.82, 0.74, 0.48, 0.75),
        "semantic": _semantic(water=0.48, sky=0.3, vegetation=0.15),
        "interest_tags": ["sports", "nightlife", "cafe"],
    },
    {
        "name": "크라비",
        "category": "beach",
        "scene": _scene(beach=0.91, nature=0.25),
        "visual": _visual(0.8, 0.76, 0.44, 0.8),
        "semantic": _semantic(water=0.46, sky=0.28, vegetation=0.2),
        "interest_tags": ["street_food", "nature", "cafe"],
    },
    {
        "name": "리우",
        "category": "beach",
        "scene": _scene(beach=0.9, festival=0.15),
        "visual": _visual(0.78, 0.82, 0.52, 0.82),
        "semantic": _semantic(water=0.4, sky=0.26, building=0.18),
        "interest_tags": ["nightlife", "street_food", "sports"],
    },
    {
        "name": "칸쿤",
        "category": "beach",
        "scene": _scene(beach=0.95, festival=0.1),
        "visual": _visual(0.84, 0.78, 0.46, 0.8),
        "semantic": _semantic(water=0.5, sky=0.3, vegetation=0.12),
        "interest_tags": ["nightlife", "street_food", "nature"],
    },
    {
        "name": "롬복",
        "category": "beach",
        "scene": _scene(beach=0.92, nature=0.18),
        "visual": _visual(0.81, 0.73, 0.43, 0.79),
        "semantic": _semantic(water=0.47, sky=0.27, vegetation=0.16),
        "interest_tags": ["nature", "cafe", "sports"],
    },
    {
        "name": "하와이",
        "category": "beach",
        "scene": _scene(beach=0.94, nature=0.15),
        "visual": _visual(0.83, 0.76, 0.45, 0.77),
        "semantic": _semantic(water=0.49, sky=0.31, vegetation=0.14),
        "interest_tags": ["nature", "sports", "cafe"],
    },
    # nature (expanded)
    {
        "name": "밴쿠버",
        "category": "nature",
        "scene": _scene(nature=0.9, beach=0.15, city=0.1),
        "visual": _visual(0.68, 0.58, 0.52, 0.42),
        "semantic": _semantic(water=0.3, vegetation=0.4, sky=0.28),
        "interest_tags": ["nature", "cafe", "sports"],
    },
    {
        "name": "인터라켄",
        "category": "nature",
        "scene": _scene(nature=0.96, culture=0.1),
        "visual": _visual(0.72, 0.55, 0.58, 0.38),
        "semantic": _semantic(vegetation=0.42, sky=0.35, water=0.2),
        "interest_tags": ["sports", "nature", "cafe"],
    },
    {
        "name": "베르겐",
        "category": "nature",
        "scene": _scene(nature=0.93, beach=0.12),
        "visual": _visual(0.6, 0.52, 0.55, 0.32),
        "semantic": _semantic(water=0.38, sky=0.38, vegetation=0.35),
        "interest_tags": ["nature", "history"],
    },
    {
        "name": "레이캬비크",
        "category": "nature",
        "scene": _scene(nature=0.95, beach=0.1),
        "visual": _visual(0.58, 0.48, 0.52, 0.28),
        "semantic": _semantic(water=0.32, sky=0.42, vegetation=0.18),
        "interest_tags": ["nature", "art"],
    },
    {
        "name": "하쿠바",
        "category": "nature",
        "scene": _scene(nature=0.92, culture=0.12),
        "visual": _visual(0.7, 0.58, 0.54, 0.38),
        "semantic": _semantic(vegetation=0.48, sky=0.32, water=0.12),
        "interest_tags": ["sports", "nature"],
    },
    {
        "name": "밴프",
        "category": "nature",
        "scene": _scene(nature=0.97, beach=0.08),
        "visual": _visual(0.74, 0.6, 0.56, 0.35),
        "semantic": _semantic(vegetation=0.5, water=0.28, sky=0.32),
        "interest_tags": ["nature", "sports"],
    },
    {
        "name": "마추픽추",
        "category": "nature",
        "scene": _scene(nature=0.96, culture=0.2),
        "visual": _visual(0.66, 0.52, 0.58, 0.42),
        "semantic": _semantic(vegetation=0.4, sky=0.35, building=0.15),
        "interest_tags": ["history", "nature", "sports"],
    },
    {
        "name": "포카라",
        "category": "nature",
        "scene": _scene(nature=0.94, culture=0.15),
        "visual": _visual(0.7, 0.55, 0.52, 0.45),
        "semantic": _semantic(vegetation=0.45, sky=0.3, water=0.18),
        "interest_tags": ["nature", "sports", "history"],
    },
    {
        "name": "장가계",
        "category": "nature",
        "scene": _scene(nature=0.98, culture=0.12),
        "visual": _visual(0.68, 0.58, 0.55, 0.4),
        "semantic": _semantic(vegetation=0.52, sky=0.32, building=0.1),
        "interest_tags": ["nature", "history", "art"],
    },
    {
        "name": "스코틀랜드 하이랜드",
        "category": "nature",
        "scene": _scene(nature=0.93, culture=0.18),
        "visual": _visual(0.58, 0.5, 0.54, 0.32),
        "semantic": _semantic(vegetation=0.48, sky=0.38, water=0.15),
        "interest_tags": ["history", "nature", "cafe"],
    },
    {
        "name": "스위스 융프라우",
        "category": "nature",
        "scene": _scene(nature=0.95, culture=0.1),
        "visual": _visual(0.7, 0.54, 0.56, 0.36),
        "semantic": _semantic(vegetation=0.44, sky=0.36, water=0.18),
        "interest_tags": ["sports", "nature", "cafe"],
    },
    # city (expanded)
    {
        "name": "런던",
        "category": "city",
        "scene": _scene(city=0.94, culture=0.2, festival=0.15),
        "visual": _visual(0.52, 0.62, 0.65, 0.38),
        "semantic": _semantic(building=0.55, sky=0.25, water=0.12),
        "interest_tags": ["art", "shopping", "history"],
    },
    {
        "name": "두바이",
        "category": "city",
        "scene": _scene(city=0.96, beach=0.1),
        "visual": _visual(0.78, 0.72, 0.62, 0.68),
        "semantic": _semantic(building=0.58, sky=0.22, water=0.15),
        "interest_tags": ["shopping", "nightlife", "art"],
    },
    {
        "name": "암스테르담",
        "category": "city",
        "scene": _scene(city=0.88, culture=0.25, festival=0.2),
        "visual": _visual(0.58, 0.68, 0.58, 0.45),
        "semantic": _semantic(building=0.48, water=0.22, sky=0.24),
        "interest_tags": ["art", "cafe", "nightlife"],
    },
    {
        "name": "서울",
        "category": "city",
        "scene": _scene(city=0.93, food=0.15, festival=0.12),
        "visual": _visual(0.58, 0.7, 0.62, 0.48),
        "semantic": _semantic(building=0.52, sky=0.2, food=0.1),
        "interest_tags": ["shopping", "nightlife", "street_food", "cafe"],
    },
    {
        "name": "시카고",
        "category": "city",
        "scene": _scene(city=0.92, festival=0.2, food=0.12),
        "visual": _visual(0.55, 0.65, 0.68, 0.42),
        "semantic": _semantic(building=0.54, sky=0.22, food=0.08),
        "interest_tags": ["art", "shopping", "nightlife"],
    },
    {
        "name": "상하이",
        "category": "city",
        "scene": _scene(city=0.95, food=0.18),
        "visual": _visual(0.54, 0.68, 0.66, 0.46),
        "semantic": _semantic(building=0.56, sky=0.2, food=0.12),
        "interest_tags": ["shopping", "street_food", "nightlife"],
    },
    {
        "name": "시드니",
        "category": "city",
        "scene": _scene(city=0.9, beach=0.15),
        "visual": _visual(0.75, 0.7, 0.55, 0.62),
        "semantic": _semantic(building=0.5, water=0.28, sky=0.3),
        "interest_tags": ["sports", "cafe", "shopping"],
    },
    {
        "name": "토론토",
        "category": "city",
        "scene": _scene(city=0.89, culture=0.18),
        "visual": _visual(0.6, 0.65, 0.6, 0.4),
        "semantic": _semantic(building=0.52, water=0.2, sky=0.24),
        "interest_tags": ["art", "shopping", "cafe"],
    },
    {
        "name": "베를린",
        "category": "city",
        "scene": _scene(city=0.9, culture=0.22, festival=0.18),
        "visual": _visual(0.56, 0.64, 0.6, 0.42),
        "semantic": _semantic(building=0.5, sky=0.24, vegetation=0.12),
        "interest_tags": ["art", "nightlife", "history"],
    },
    {
        "name": "로스앤젤레스",
        "category": "city",
        "scene": _scene(city=0.91, beach=0.12, festival=0.15),
        "visual": _visual(0.8, 0.72, 0.58, 0.72),
        "semantic": _semantic(building=0.48, sky=0.28, water=0.14),
        "interest_tags": ["shopping", "nightlife", "art"],
    },
    # culture (expanded)
    {
        "name": "카이로",
        "category": "culture",
        "scene": _scene(culture=0.94, city=0.2),
        "visual": _visual(0.75, 0.62, 0.52, 0.72),
        "semantic": _semantic(building=0.42, sky=0.28, vegetation=0.1),
        "interest_tags": ["history", "art", "local_market"],
    },
    {
        "name": "아테네",
        "category": "culture",
        "scene": _scene(culture=0.96, beach=0.12),
        "visual": _visual(0.78, 0.65, 0.52, 0.68),
        "semantic": _semantic(building=0.45, sky=0.3, water=0.18),
        "interest_tags": ["history", "art", "cafe"],
    },
    {
        "name": "마라케시",
        "category": "culture",
        "scene": _scene(culture=0.92, food=0.15),
        "visual": _visual(0.76, 0.7, 0.5, 0.78),
        "semantic": _semantic(building=0.38, sky=0.26, food=0.12),
        "interest_tags": ["local_market", "history", "street_food"],
    },
    {
        "name": "바라나시",
        "category": "culture",
        "scene": _scene(culture=0.95, food=0.12),
        "visual": _visual(0.68, 0.58, 0.48, 0.62),
        "semantic": _semantic(building=0.35, sky=0.28, vegetation=0.15),
        "interest_tags": ["history", "art", "local_market"],
    },
    {
        "name": "페트라",
        "category": "culture",
        "scene": _scene(culture=0.97, nature=0.25),
        "visual": _visual(0.72, 0.55, 0.55, 0.65),
        "semantic": _semantic(building=0.42, sky=0.32, vegetation=0.2),
        "interest_tags": ["history", "art"],
    },
    {
        "name": "쿠스코",
        "category": "culture",
        "scene": _scene(culture=0.96, nature=0.35),
        "visual": _visual(0.7, 0.58, 0.52, 0.55),
        "semantic": _semantic(vegetation=0.38, building=0.32, sky=0.28),
        "interest_tags": ["history", "local_market", "art"],
    },
    {
        "name": "라사",
        "category": "culture",
        "scene": _scene(culture=0.94, nature=0.3),
        "visual": _visual(0.65, 0.52, 0.5, 0.48),
        "semantic": _semantic(building=0.3, sky=0.35, vegetation=0.2),
        "interest_tags": ["history", "art"],
    },
    {
        "name": "예루살렘",
        "category": "culture",
        "scene": _scene(culture=0.95, city=0.15),
        "visual": _visual(0.74, 0.6, 0.52, 0.62),
        "semantic": _semantic(building=0.4, sky=0.28, vegetation=0.12),
        "interest_tags": ["history", "art", "local_market"],
    },
    {
        "name": "플로렌스",
        "category": "culture",
        "scene": _scene(culture=0.93, food=0.15, city=0.12),
        "visual": _visual(0.74, 0.66, 0.5, 0.68),
        "semantic": _semantic(building=0.42, sky=0.26, food=0.1),
        "interest_tags": ["art", "history", "cafe"],
    },
    {
        "name": "부다페스트",
        "category": "culture",
        "scene": _scene(culture=0.9, city=0.22, festival=0.15),
        "visual": _visual(0.62, 0.64, 0.54, 0.52),
        "semantic": _semantic(building=0.48, water=0.22, sky=0.24),
        "interest_tags": ["history", "cafe", "nightlife"],
    },
    {
        "name": "체코 프라하",
        "category": "culture",
        "scene": _scene(culture=0.92, city=0.25, festival=0.18),
        "visual": _visual(0.58, 0.62, 0.56, 0.45),
        "semantic": _semantic(building=0.5, sky=0.26, vegetation=0.14),
        "interest_tags": ["history", "art", "cafe"],
    },
    # festival (expanded)
    {
        "name": "리우 카니발",
        "category": "festival",
        "scene": _scene(festival=0.97, beach=0.15, culture=0.12),
        "visual": _visual(0.76, 0.88, 0.58, 0.82),
        "semantic": _semantic(water=0.28, sky=0.26, building=0.18),
        "interest_tags": ["nightlife", "street_food", "sports"],
    },
    {
        "name": "인도 홀리축제",
        "category": "festival",
        "scene": _scene(festival=0.94, culture=0.25),
        "visual": _visual(0.72, 0.85, 0.52, 0.75),
        "semantic": _semantic(building=0.32, sky=0.28, vegetation=0.15),
        "interest_tags": ["street_food", "history", "local_market"],
    },
    {
        "name": "스페인 토마토축제",
        "category": "festival",
        "scene": _scene(festival=0.92, food=0.15),
        "visual": _visual(0.78, 0.82, 0.5, 0.72),
        "semantic": _semantic(building=0.3, sky=0.28, food=0.12),
        "interest_tags": ["street_food", "sports", "nightlife"],
    },
    {
        "name": "옥토버페스트",
        "category": "festival",
        "scene": _scene(festival=0.93, food=0.2, city=0.15),
        "visual": _visual(0.65, 0.75, 0.55, 0.55),
        "semantic": _semantic(building=0.4, sky=0.24, food=0.15),
        "interest_tags": ["street_food", "nightlife", "history"],
    },
    {
        "name": "교토 기온마츠리",
        "category": "festival",
        "scene": _scene(festival=0.91, culture=0.35),
        "visual": _visual(0.62, 0.68, 0.52, 0.52),
        "semantic": _semantic(building=0.38, vegetation=0.3, sky=0.22),
        "interest_tags": ["history", "art", "cafe"],
    },
    {
        "name": "태국 송끄란",
        "category": "festival",
        "scene": _scene(festival=0.9, beach=0.12, food=0.1),
        "visual": _visual(0.8, 0.82, 0.48, 0.78),
        "semantic": _semantic(water=0.25, sky=0.28, building=0.2),
        "interest_tags": ["street_food", "nightlife", "sports"],
    },
    {
        "name": "살바도르",
        "category": "festival",
        "scene": _scene(festival=0.89, beach=0.18, culture=0.2),
        "visual": _visual(0.74, 0.84, 0.54, 0.8),
        "semantic": _semantic(water=0.3, sky=0.26, building=0.22),
        "interest_tags": ["nightlife", "street_food", "sports"],
    },
    {
        "name": "에든버러 페스티벌",
        "category": "festival",
        "scene": _scene(festival=0.9, culture=0.32),
        "visual": _visual(0.54, 0.62, 0.6, 0.34),
        "semantic": _semantic(building=0.46, sky=0.34, vegetation=0.18),
        "interest_tags": ["art", "history", "nightlife"],
    },
    {
        "name": "시안 춘절",
        "category": "festival",
        "scene": _scene(festival=0.93, culture=0.3, city=0.15),
        "visual": _visual(0.58, 0.72, 0.58, 0.48),
        "semantic": _semantic(building=0.42, sky=0.26, food=0.1),
        "interest_tags": ["history", "art", "street_food"],
    },
    {
        "name": "벨기에 겐트 페스티벌",
        "category": "festival",
        "scene": _scene(festival=0.88, culture=0.28, city=0.12),
        "visual": _visual(0.6, 0.7, 0.54, 0.48),
        "semantic": _semantic(building=0.44, water=0.2, sky=0.24),
        "interest_tags": ["art", "cafe", "history"],
    },
    {
        "name": "라스베가스",
        "category": "festival",
        "scene": _scene(festival=0.96, city=0.45),
        "visual": _visual(0.72, 0.8, 0.65, 0.55),
        "semantic": _semantic(building=0.52, sky=0.18, food=0.08),
        "interest_tags": ["nightlife", "shopping", "art"],
    },
    {
        "name": "뮌헨 옥토버페스트",
        "category": "festival",
        "scene": _scene(festival=0.91, food=0.22, city=0.12),
        "visual": _visual(0.64, 0.74, 0.54, 0.52),
        "semantic": _semantic(building=0.38, sky=0.22, food=0.14),
        "interest_tags": ["street_food", "nightlife", "history"],
    },
    # food (expanded)
    {
        "name": "리마",
        "category": "food",
        "scene": _scene(food=0.93, culture=0.2, beach=0.1),
        "visual": _visual(0.72, 0.75, 0.5, 0.65),
        "semantic": _semantic(food=0.32, building=0.3, water=0.15),
        "interest_tags": ["street_food", "local_market", "history"],
    },
    {
        "name": "홍콩 (미식)",
        "category": "food",
        "scene": _scene(food=0.94, city=0.28),
        "visual": _visual(0.58, 0.72, 0.62, 0.52),
        "semantic": _semantic(food=0.35, building=0.45, water=0.1),
        "interest_tags": ["street_food", "shopping", "local_market"],
    },
    {
        "name": "마라케시 (미식)",
        "category": "food",
        "scene": _scene(food=0.91, culture=0.28),
        "visual": _visual(0.74, 0.72, 0.5, 0.76),
        "semantic": _semantic(food=0.3, building=0.32, sky=0.22),
        "interest_tags": ["street_food", "local_market", "history"],
    },
    {
        "name": "싱가포르 (미식)",
        "category": "food",
        "scene": _scene(food=0.95, city=0.22, beach=0.08),
        "visual": _visual(0.7, 0.74, 0.52, 0.58),
        "semantic": _semantic(food=0.38, building=0.35, water=0.12),
        "interest_tags": ["street_food", "local_market", "shopping"],
    },
    {
        "name": "뭄바이",
        "category": "food",
        "scene": _scene(food=0.92, city=0.25, culture=0.15),
        "visual": _visual(0.68, 0.78, 0.55, 0.68),
        "semantic": _semantic(food=0.34, building=0.4, sky=0.18),
        "interest_tags": ["street_food", "local_market", "history"],
    },
    {
        "name": "리옹",
        "category": "food",
        "scene": _scene(food=0.94, culture=0.22, city=0.12),
        "visual": _visual(0.65, 0.68, 0.52, 0.55),
        "semantic": _semantic(food=0.36, building=0.35, sky=0.2),
        "interest_tags": ["cafe", "street_food", "art"],
    },
    {
        "name": "도쿄 츠키지",
        "category": "food",
        "scene": _scene(food=0.96, city=0.32, culture=0.1),
        "visual": _visual(0.6, 0.7, 0.58, 0.48),
        "semantic": _semantic(food=0.4, building=0.42, sky=0.14),
        "interest_tags": ["street_food", "local_market", "shopping"],
    },
    {
        "name": "바르셀로나 (미식)",
        "category": "food",
        "scene": _scene(food=0.93, beach=0.1, culture=0.2),
        "visual": _visual(0.76, 0.74, 0.48, 0.72),
        "semantic": _semantic(food=0.33, building=0.36, water=0.14),
        "interest_tags": ["street_food", "cafe", "art"],
    },
    {
        "name": "부에노스아이레스",
        "category": "food",
        "scene": _scene(food=0.9, culture=0.22, city=0.15),
        "visual": _visual(0.7, 0.72, 0.52, 0.62),
        "semantic": _semantic(food=0.3, building=0.36, sky=0.22),
        "interest_tags": ["street_food", "cafe", "nightlife"],
    },
    {
        "name": "타이페이",
        "category": "food",
        "scene": _scene(food=0.91, city=0.28, culture=0.12),
        "visual": _visual(0.62, 0.74, 0.58, 0.52),
        "semantic": _semantic(food=0.36, building=0.38, sky=0.16),
        "interest_tags": ["street_food", "local_market", "cafe"],
    },
    {
        "name": "호치민",
        "category": "food",
        "scene": _scene(food=0.92, city=0.22, culture=0.12),
        "visual": _visual(0.72, 0.8, 0.5, 0.7),
        "semantic": _semantic(food=0.34, building=0.34, vegetation=0.1),
        "interest_tags": ["street_food", "local_market", "history"],
    },
    {
        "name": "서울 (미식)",
        "category": "food",
        "scene": _scene(food=0.93, city=0.3, festival=0.1),
        "visual": _visual(0.6, 0.72, 0.58, 0.5),
        "semantic": _semantic(food=0.36, building=0.4, sky=0.16),
        "interest_tags": ["street_food", "local_market", "nightlife"],
    },
)


_CATEGORY_POOLS: Dict[str, List[Dict[str, Any]]] = {
    cat: [p for p in _DESTINATION_PROFILES if p["category"] == cat]
    for cat in SCENE_CATEGORIES
}


def _pick_destination_count() -> int:
    upper = min(_MAX_DESTINATIONS, max(_MIN_DESTINATIONS, len(_DESTINATION_PROFILES)))
    return random.randint(_MIN_DESTINATIONS, upper)


def _resolve_top_category(preference_vector: Mapping[str, Any]) -> str:
    """
    Use the highest scene score (same rule as ensemble_vectors / frontend bars).
    Falls back to top_category when scene is missing.
    """
    scene = preference_vector.get("scene")
    if isinstance(scene, Mapping) and scene:
        best_key = max(scene, key=lambda k: float(scene.get(k, 0.0)))
        cat = str(best_key).strip().lower()
        if cat in _CATEGORY_POOLS:
            return cat
    fallback = str(preference_vector.get("top_category", "")).strip().lower()
    if fallback in _CATEGORY_POOLS:
        return fallback
    return "nature"


def _resolve_category_pool(top_category: str) -> List[Dict[str, Any]]:
    cat = str(top_category).strip().lower()
    if cat in _CATEGORY_POOLS and _CATEGORY_POOLS[cat]:
        return _CATEGORY_POOLS[cat]
    return list(_DESTINATION_PROFILES)


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


def _normalize_interest_tags(
    interest_tags: Optional[List[str]],
) -> set[str]:
    if not interest_tags:
        return set()
    out: set[str] = set()
    for tag in interest_tags:
        if isinstance(tag, str) and tag.strip():
            out.add(tag.strip().lower())
    return out


def _interest_bonus(user_tags: set[str], dest_tags: Sequence[str]) -> float:
    if not user_tags or not dest_tags:
        return 0.0
    dest_set = {str(t).strip().lower() for t in dest_tags if str(t).strip()}
    matches = len(user_tags & dest_set)
    return min(matches * _INTEREST_MATCH_BONUS, _INTEREST_BONUS_MAX)


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
    detected_objects: Optional[set] = None,
) -> Tuple[bool, str]:
    if detected_objects is not None:
        if len(detected_objects & _HOMEBODY_KEYWORDS) >= 2:
            return True, "homebody"

    if photo_top_categories and _categories_all_different(photo_top_categories):
        return True, "unpredictable"

    if bool(preference_vector.get("is_uncertain", False)):
        return True, "uncertain"
    if float(preference_vector.get("confidence", 0.0)) < _UNCERTAIN_THRESHOLD:
        return True, "uncertain"
    scene = preference_vector.get("scene", {})
    if isinstance(scene, Mapping) and _all_scene_below_threshold(scene, _UNCERTAIN_THRESHOLD):
        return True, "uncertain"

    return False, ""


def _random_recommendation(
    preference_vector: Mapping[str, Any],
    reason: str = "uncertain",
) -> Dict[str, Any]:
    top_category = _resolve_top_category(preference_vector)
    pool = _resolve_category_pool(top_category)
    k = min(_pick_destination_count(), len(pool))
    chosen_profiles = random.sample(pool, k=k)
    chosen = [str(p["name"]) for p in chosen_profiles]
    scores = {name: round(random.uniform(0.5, 0.85), 2) for name in chosen}

    if reason == "homebody":
        message = random.choice(_HOMEBODY_MESSAGES)
    elif reason == "unpredictable":
        message = random.choice(_UNPREDICTABLE_MESSAGES)
    else:
        message = "취향을 파악하기 어려워서 랜덤 추천드려요!"

    return {
        "destinations": chosen,
        "top_category": top_category,
        "is_random": True,
        "scores": scores,
        "reason": reason,
        "message": message,
    }


def recommend(
    preference_vector: Mapping[str, Any],
    photo_top_categories: Optional[Sequence[str]] = None,
    detected_objects: Optional[set] = None,
    interest_tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Recommend Top-3 destinations via cosine similarity + interest-tag bonus.

    photo_top_categories: top_category from each photo in a session; if all differ, triggers random mode.
    interest_tags: user interest tag strings; +0.05 per overlap with destination (max +0.20).
    """
    top_category = _resolve_top_category(preference_vector)

    use_random, reason = _should_use_random(
        preference_vector, photo_top_categories, detected_objects
    )
    if use_random:
        return _random_recommendation(preference_vector, reason=reason)

    user_vec = _preference_to_array(preference_vector)
    user_interests = _normalize_interest_tags(interest_tags)
    pool = _resolve_category_pool(top_category)
    ranked_profiles: List[Tuple[Dict[str, Any], float]] = []

    for profile in pool:
        dest_vec = _flatten_vector(
            profile["scene"],
            profile["visual"],
            _fix_semantic(profile["semantic"]),
        )
        cosine = _cosine_similarity(user_vec, dest_vec)
        bonus = _interest_bonus(
            user_interests, profile.get("interest_tags", [])
        )
        score = cosine + bonus
        ranked_profiles.append((profile, score))

    ranked_profiles.sort(key=lambda x: (-x[1], x[0]["name"]))

    k = min(_pick_destination_count(), len(ranked_profiles))
    # 상위 후보 중 무작위 샘플: 유사도는 유지하면서 매번 다른 조합
    shortlist_size = max(k, min(len(ranked_profiles), k * 3))
    shortlist = ranked_profiles[:shortlist_size]
    chosen_pairs = random.sample(shortlist, k=k)

    destinations = [str(p["name"]) for p, _ in chosen_pairs]
    scores = {str(p["name"]): round(score, 2) for p, score in chosen_pairs}

    return {
        "destinations": destinations,
        "top_category": top_category,
        "is_random": False,
        "scores": scores,
        "reason": "",
        "message": "",
    }
