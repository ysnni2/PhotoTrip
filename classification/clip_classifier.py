"""Zero-shot scene classification with OpenAI CLIP ViT-B/32."""

from __future__ import annotations

from typing import Dict

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

MODEL_ID = "openai/clip-vit-base-patch32"

_CATEGORIES = ("Beach", "Nature", "City", "Indoor")
_TEXT_PROMPTS = (
    "a photo of a beach",
    "a photo of nature",
    "a photo of a city",
    "a photo of an indoor scene",
)

_model: CLIPModel | None = None
_processor: CLIPProcessor | None = None


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_model() -> tuple[CLIPModel, CLIPProcessor]:
    global _model, _processor
    if _model is None or _processor is None:
        _processor = CLIPProcessor.from_pretrained(MODEL_ID)
        _model = CLIPModel.from_pretrained(MODEL_ID).to(_device())
        _model.eval()
    return _model, _processor


def classify(image: Image.Image) -> Dict[str, float]:
    """
    Zero-shot classify a PIL image into Beach / Nature / City / Indoor.

    Returns a dict of category names to probabilities (softmax over CLIP logits).
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    model, processor = _load_model()
    device = next(model.parameters()).device

    inputs = processor(
        text=list(_TEXT_PROMPTS),
        images=image,
        return_tensors="pt",
        padding=True,
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.inference_mode():
        outputs = model(**inputs)
        logits = outputs.logits_per_image
        probs = logits.softmax(dim=1)[0]

    return {label: float(probs[i]) for i, label in enumerate(_CATEGORIES)}
