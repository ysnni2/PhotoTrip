"""CLIP zero-shot image style scoring."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

MODEL_ID = "openai/clip-vit-base-patch32"

STYLE_PROMPTS: Dict[str, str] = {
    "luxury": "a luxury elegant expensive high-end place",
    "cozy": "a cozy warm comfortable intimate atmosphere",
    "vibrant": "a vibrant colorful energetic lively scene",
    "minimal": "a minimal clean simple modern space",
    "romantic": "a romantic soft dreamy beautiful atmosphere",
    "adventurous": "a adventurous wild outdoor rugged scene",
}

STYLE_NAMES: List[str] = list(STYLE_PROMPTS.keys())

_model: Optional[CLIPModel] = None
_processor: Optional[CLIPProcessor] = None
_text_features: Optional[torch.Tensor] = None
_device: Optional[torch.device] = None


def _get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _image_features(model: CLIPModel, pixel_values: torch.Tensor) -> torch.Tensor:
    feats = model.get_image_features(pixel_values=pixel_values)
    if not isinstance(feats, torch.Tensor):
        feats = feats.pooler_output
    return feats / feats.norm(dim=-1, keepdim=True)


def _encode_text_features(
    model: CLIPModel,
    processor: CLIPProcessor,
    device: torch.device,
) -> torch.Tensor:
    texts = [STYLE_PROMPTS[name] for name in STYLE_NAMES]
    batch = processor(text=texts, return_tensors="pt", padding=True)
    batch = {k: v.to(device) for k, v in batch.items()}
    with torch.inference_mode():
        feats = model.get_text_features(**batch)
        if not isinstance(feats, torch.Tensor):
            feats = feats.pooler_output
        feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats


def _load() -> Tuple[CLIPModel, CLIPProcessor, torch.Tensor, torch.device]:
    global _model, _processor, _text_features, _device

    if (
        _model is not None
        and _processor is not None
        and _text_features is not None
        and _device is not None
    ):
        return _model, _processor, _text_features, _device

    device = _get_device()
    processor = CLIPProcessor.from_pretrained(MODEL_ID)
    model = CLIPModel.from_pretrained(MODEL_ID)
    model.to(device)
    model.eval()

    text_features = _encode_text_features(model, processor, device)

    _model = model
    _processor = processor
    _text_features = text_features
    _device = device
    return model, processor, text_features, device


def analyze_style(image: Image.Image) -> Dict[str, float]:
    """
    Score a PIL image against six style prompts via CLIP zero-shot.

    Returns softmax probabilities, e.g. {"luxury": 0.12, "cozy": 0.35, ...}.
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    model, processor, text_features, device = _load()
    batch = processor(images=image, return_tensors="pt")
    pixel_values = batch["pixel_values"].to(device)

    with torch.inference_mode():
        image_feats = _image_features(model, pixel_values)
        logits = image_feats @ text_features.T * model.logit_scale.exp()
        probs = logits.softmax(dim=-1)[0].cpu()

    return {name: float(probs[i]) for i, name in enumerate(STYLE_NAMES)}
