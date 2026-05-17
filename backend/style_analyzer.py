"""SigLIP zero-shot image style scoring."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor

MODEL_ID = "google/siglip-large-patch16-256"

STYLE_PROMPTS: Dict[str, str] = {
    "luxury": "a luxury elegant expensive high-end place",
    "cozy": "a cozy warm comfortable intimate atmosphere",
    "vibrant": "a vibrant colorful energetic lively scene",
    "minimal": "a minimal clean simple modern space",
    "romantic": "a romantic soft dreamy beautiful atmosphere",
    "adventurous": "a adventurous wild outdoor rugged scene",
}

STYLE_NAMES: List[str] = list(STYLE_PROMPTS.keys())

_model: Optional[Any] = None
_processor: Optional[Any] = None
_text_features: Optional[torch.Tensor] = None
_device: Optional[torch.device] = None


def _get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _normalize_features(feats: Any) -> torch.Tensor:
    if not isinstance(feats, torch.Tensor):
        feats = feats.pooler_output
    return feats / feats.norm(dim=-1, keepdim=True)


def _image_features(model: torch.nn.Module, pixel_values: torch.Tensor) -> torch.Tensor:
    feats = model.get_image_features(pixel_values=pixel_values)
    return _normalize_features(feats)


def _text_features(model: torch.nn.Module, text_batch: Dict[str, torch.Tensor]) -> torch.Tensor:
    feats = model.get_text_features(**text_batch)
    return _normalize_features(feats)


def _zeroshot_logits(
    model: torch.nn.Module,
    image_feats: torch.Tensor,
    text_feats: torch.Tensor,
) -> torch.Tensor:
    logits = image_feats @ text_feats.T * model.logit_scale.exp()
    if getattr(model, "logit_bias", None) is not None:
        logits = logits + model.logit_bias
    return logits


def _encode_text_features(
    model: torch.nn.Module,
    processor: Any,
    device: torch.device,
) -> torch.Tensor:
    texts = [STYLE_PROMPTS[name] for name in STYLE_NAMES]
    batch = processor(text=texts, return_tensors="pt", padding=True)
    batch = {k: v.to(device) for k, v in batch.items()}
    with torch.inference_mode():
        return _text_features(model, batch)


def _load() -> Tuple[Any, Any, torch.Tensor, torch.device]:
    global _model, _processor, _text_features, _device

    if (
        _model is not None
        and _processor is not None
        and _text_features is not None
        and _device is not None
    ):
        return _model, _processor, _text_features, _device

    device = _get_device()
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID)
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
    Score a PIL image against six style prompts via SigLIP zero-shot.

    Returns softmax probabilities, e.g. {"luxury": 0.12, "cozy": 0.35, ...}.
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    model, processor, text_features, device = _load()
    batch = processor(images=image, return_tensors="pt")
    pixel_values = batch["pixel_values"].to(device)

    with torch.inference_mode():
        image_feats = _image_features(model, pixel_values)
        logits = _zeroshot_logits(model, image_feats, text_features)
        probs = logits.softmax(dim=-1)[0].cpu()

    return {name: float(probs[i]) for i, name in enumerate(STYLE_NAMES)}
