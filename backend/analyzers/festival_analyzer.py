"""Festival CV evidence + optional Gemini subtype."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from PIL import Image


def extract_festival_cv_evidence(opencv_result: Mapping[str, float]) -> Dict[str, float]:
    brightness = float(opencv_result.get("brightness", 0.5))
    saturation = float(opencv_result.get("saturation", 0.5))
    contrast = float(opencv_result.get("contrast", 0.5))
    warm_tone = float(opencv_result.get("warm_tone", 0.5))
    person_ratio = float(opencv_result.get("person_ratio", 0.0))

    crowd_score = min(1.0, person_ratio * 8.0)
    vivid_tone = min(1.0, max(0.0, (saturation - 0.35) / 0.55))
    night_lighting = min(1.0, max(0.0, (0.65 - brightness) / 0.55))

    return {
        "crowd_score": round(crowd_score, 4),
        "vivid_tone": round(vivid_tone, 4),
        "night_lighting": round(night_lighting, 4),
        "high_contrast": round(min(1.0, max(0.0, (contrast - 0.25) / 0.55)), 4),
        "warm_lighting": round(min(1.0, max(0.0, (warm_tone - 0.45) / 0.45)), 4),
    }


def needs_gemini_fallback(festival_conf: float, evidence: Mapping[str, float]) -> bool:
    if 0.3 <= festival_conf <= 0.6:
        return True
    crowd = float(evidence.get("crowd_score", 0.0))
    stage_light = (
        float(evidence.get("night_lighting", 0.0)) * 0.5
        + float(evidence.get("vivid_tone", 0.0)) * 0.5
    )
    return crowd >= 0.35 and stage_light < 0.35


def analyze_festival(
    image: Image.Image,
    *,
    opencv_result: Optional[Mapping[str, float]] = None,
    category_scores: Optional[Mapping[str, float]] = None,
    use_gemini: bool = True,
) -> Dict[str, Any]:
    if opencv_result is None:
        from opencv_analyzer import analyze as analyze_opencv

        opencv_result = analyze_opencv(image)
    if category_scores is None:
        from .category_analyzer import analyze_category

        category_scores = analyze_category(image)

    fest_conf = float(category_scores.get("festival", 0.0))
    evidence = extract_festival_cv_evidence(opencv_result)
    gemini_needed = needs_gemini_fallback(fest_conf, evidence)

    subtype = "not_festival"
    confidence = 0.0
    gemini_used = False

    if gemini_needed and use_gemini:
        try:
            from gemini_explainer import classify_festival_subtype

            gem = classify_festival_subtype(image, evidence)
            if gem.get("gemini_fallback_used"):
                subtype = str(gem.get("festival_subtype", "not_festival"))
                confidence = float(gem.get("festival_confidence", 0.0))
                gemini_used = True
        except Exception:
            pass

    if not gemini_used:
        if fest_conf >= 0.35 or evidence["crowd_score"] >= 0.35:
            subtype = "festival"
            confidence = max(fest_conf, evidence["crowd_score"] * 0.5)

    return {
        "festival_evidence": {
            "crowd_score": evidence["crowd_score"],
            "vivid_tone": evidence["vivid_tone"],
            "night_lighting": evidence["night_lighting"],
        },
        "festival_subtype": subtype,
        "festival_confidence": round(confidence, 4),
        "gemini_fallback_used": gemini_used,
        "gemini_fallback_needed": gemini_needed and not gemini_used,
    }
