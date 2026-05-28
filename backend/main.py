from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import io
import sys
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_FRONTEND_DIR = _PROJECT_ROOT / "frontend"

if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from siglip_classifier import classify_with_fallback  # noqa: E402
from oneformer import segment, segment_ratios  # noqa: E402
from opencv_analyzer import analyze  # noqa: E402
from preference_vector import SCENE_CATEGORIES, build_vector  # noqa: E402
from recommender import recommend  # noqa: E402
from gemini_explainer import _generate, explain, random_explain  # noqa: E402
from style_analyzer import analyze_style  # noqa: E402
from analyzers.lifestyle_analyzer import analyze_lifestyle  # noqa: E402

app = FastAPI(title="PhotoTrip CV API")


class ChatRequest(BaseModel):
    message: str
    context: dict = {}


class RouletteRequest(BaseModel):
    preference_vector: dict
    category: str


if _FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR)), name="static")


def ensemble_vectors(vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Average scene/visual/semantic/style across per-image preference vectors."""
    if not vectors:
        raise ValueError("vectors must not be empty")
    if len(vectors) == 1:
        return dict(vectors[0])

    n = len(vectors)

    scene = {
        cat: sum(float(v.get("scene", {}).get(cat, 0.0)) for v in vectors) / n
        for cat in SCENE_CATEGORIES
    }
    visual_keys = set()
    semantic_keys = set()
    style_keys = set()
    for v in vectors:
        visual_keys.update((v.get("visual") or {}).keys())
        semantic_keys.update((v.get("semantic") or {}).keys())
        style_keys.update((v.get("style") or {}).keys())

    visual = {
        k: sum(float((v.get("visual") or {}).get(k, 0.0)) for v in vectors) / n
        for k in visual_keys
    }
    semantic = {
        k: sum(float((v.get("semantic") or {}).get(k, 0.0)) for v in vectors) / n
        for k in semantic_keys
    }
    style = {
        k: sum(float((v.get("style") or {}).get(k, 0.0)) for v in vectors) / n
        for k in style_keys
    }

    top_category = max(scene, key=scene.get) if scene else ""
    confidence = sum(float(v.get("confidence", 0.0)) for v in vectors) / n
    max_style = max(style.values()) if style else 0.0
    is_uncertain = confidence < 0.3 or max_style < 0.15

    return {
        "scene": scene,
        "visual": visual,
        "semantic": semantic,
        "style": style,
        "top_category": top_category,
        "confidence": confidence,
        "is_uncertain": is_uncertain,
    }


@app.get("/")
async def serve_index() -> FileResponse:
    index_path = _FRONTEND_DIR / "index.html"
    return FileResponse(index_path)


@app.post("/api/analyze")
async def analyze_image(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="At least one image file is required")

    vectors: List[Dict[str, Any]] = []
    detected_objects: set[str] = set()

    for file in files:
        raw = await file.read()
        image = Image.open(io.BytesIO(raw)).convert("RGB")

        clip_result = classify_with_fallback(
            image, use_tta=True, temperature=1.1
        )
        segment_result = segment(image)
        seg_ratios = segment_ratios(segment_result)
        opencv_result = analyze(image)
        style_result = analyze_style(image, opencv_result)
        lifestyle_result = analyze_lifestyle(image)

        pv = build_vector(
            clip_result, seg_ratios, opencv_result, style_result, lifestyle_result
        )
        pv["segment_ratios"] = seg_ratios
        pv["segment_mask_base64"] = str(segment_result.get("mask_base64", ""))
        vectors.append(pv)
        detected_objects.update(seg_ratios.keys())

    final_vector = ensemble_vectors(vectors)
    photo_top_categories = [str(v.get("top_category", "")) for v in vectors]

    recommendation = recommend(
        final_vector,
        photo_top_categories=photo_top_categories,
        detected_objects=detected_objects,
    )

    if recommendation.get("is_random"):
        gemini_text = random_explain(recommendation.get("reason", "uncertain"))
    else:
        gemini_text = explain(final_vector, recommendation)

    return {
        "preference_vector": final_vector,
        "recommendation": recommendation,
        "gemini_text": gemini_text,
        "per_image": vectors,
    }


@app.post("/api/roulette-finish")
async def roulette_finish(body: RouletteRequest) -> Dict[str, Any]:
    """Apply roulette category, refresh recommendations and Gemini text."""
    cat = str(body.category).strip().lower()
    if cat not in SCENE_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category: {cat}")

    pv = dict(body.preference_vector)
    scene = {c: float((pv.get("scene") or {}).get(c, 0.0)) * 0.35 for c in SCENE_CATEGORIES}
    scene[cat] = max(scene.get(cat, 0.0), 0.82)
    pv["scene"] = scene
    pv["top_category"] = cat
    pv["confidence"] = max(float(pv.get("confidence", 0.0)), scene[cat])
    pv["is_uncertain"] = False

    recommendation = recommend(pv)
    gemini_text = explain(pv, recommendation)

    return {
        "preference_vector": pv,
        "recommendation": recommendation,
        "gemini_text": gemini_text,
    }


@app.post("/api/chat")
async def chat(body: ChatRequest) -> dict:
    prompt = f"""너는 여행 추천 앱 PhotoTrip의 AI 가이드야.
사용자 취향 데이터: {body.context}
사용자 질문: {body.message}

조건:
- 한국어로 친근하고 따뜻하게 답변
- 취향 데이터 기반으로 구체적으로 답변
- 2~4문장 이내
- 이모지 없이 본문만"""

    try:
        reply = _generate(prompt)
        return {"reply": reply}
    except Exception:
        return {"reply": "잠시 후 다시 시도해주세요."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
