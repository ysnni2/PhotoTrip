"""Gradio UI: image → CLIP / SegFormer / OpenCV → preference → travel Top-3."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import gradio as gr
from PIL import Image

from classification.clip_classifier import classify
from classification.opencv_analyzer import analyze
from preference.preference_vector import generate
from recommendation.recommender import recommend
from segmentation.segformer import segment


def _ensure_pil(image: Image.Image | None) -> Image.Image | None:
    if image is None:
        return None
    if not isinstance(image, Image.Image):
        pil = Image.fromarray(image)
        return pil.convert("RGB") if pil.mode != "RGB" else pil
    return image.convert("RGB") if image.mode != "RGB" else image


def run_pipeline(image: Image.Image | None):
    """Returns five JSON-serializable payloads for gr.JSON."""
    empty: dict | list = {}
    empty_list: list = []
    pil = _ensure_pil(image)
    if pil is None:
        return empty, empty, empty, empty, empty_list

    clip_result = classify(pil)
    seg_result = segment(pil)
    cv_result = analyze(pil)
    preference_vector = generate(clip_result, seg_result, cv_result)
    top3 = recommend(preference_vector)

    return clip_result, seg_result, cv_result, preference_vector, top3


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Travel preference from image") as demo:
        gr.Markdown(
            "## 이미지 기반 여행 취향 분석\n"
            "이미지를 업로드한 뒤 **분석 실행**을 누르면 CLIP, SegFormer, OpenCV 결과와 "
            "Preference Vector, Top-3 추천이 JSON으로 표시됩니다."
        )
        image_in = gr.Image(type="pil", label="이미지 업로드")
        run_btn = gr.Button("분석 실행", variant="primary")

        gr.Markdown("### 결과")
        clip_json = gr.JSON(label="CLIP 분류 결과")
        seg_json = gr.JSON(label="SegFormer 픽셀 비율")
        cv_json = gr.JSON(label="OpenCV 색상 분석")
        pref_json = gr.JSON(label="Preference Vector")
        rec_json = gr.JSON(label="Top-3 여행지 추천")

        run_btn.click(
            fn=run_pipeline,
            inputs=[image_in],
            outputs=[clip_json, seg_json, cv_json, pref_json, rec_json],
        )

    return demo


if __name__ == "__main__":
    build_demo().launch(share=False, server_port=7860)
