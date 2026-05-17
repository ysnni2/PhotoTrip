from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import io
import sys
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_FRONTEND_DIR = _PROJECT_ROOT / "frontend"

if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from siglip_classifier import classify  # noqa: E402
from mask2former import segment  # noqa: E402
from opencv_analyzer import analyze  # noqa: E402
from preference_vector import SCENE_CATEGORIES, build_vector  # noqa: E402
from recommender import recommend  # noqa: E402
from gemini_explainer import explain, random_explain  # noqa: E402
from style_analyzer import analyze_style  # noqa: E402

app = FastAPI(title="PhotoTrip CV API")

if _FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR)), name="static")


def _clip_result_from_scores(scores: Dict[str, float]) -> Dict[str, Any]:
    """Map classify() softmax dict to build_vector() clip_result shape."""
    all_scores: Dict[str, float] = {}
    for cat in SCENE_CATEGORIES:
        all_scores[cat] = float(
            scores.get(cat, scores.get(cat.capitalize(), 0.0))
        )
    top_category = max(all_scores, key=all_scores.get) if all_scores else ""
    return {
        "category": top_category,
        "confidence": all_scores.get(top_category, 0.0),
        "all_scores": all_scores,
    }


@app.get("/")
async def serve_index() -> FileResponse:
    index_path = _FRONTEND_DIR / "index.html"
    return FileResponse(index_path)


@app.post("/api/analyze")
async def analyze_image(file: UploadFile = File(...)) -> Dict[str, Any]:
    raw = await file.read()
    image = Image.open(io.BytesIO(raw)).convert("RGB")

    clip_scores = classify(image)
    clip_result = _clip_result_from_scores(clip_scores)
    segment_result = segment(image)
    opencv_result = analyze(image)
    style_result = analyze_style(image, opencv_result)

    preference_vector = build_vector(
        clip_result, segment_result, opencv_result, style_result
    )
    recommendation = recommend(preference_vector)

    if recommendation.get("is_random"):
        gemini_text = random_explain()
    else:
        gemini_text = explain(preference_vector, recommendation)

    return {
        "preference_vector": preference_vector,
        "recommendation": recommendation,
        "gemini_text": gemini_text,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
