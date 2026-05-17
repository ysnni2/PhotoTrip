"""SigLIP zero-shot image style scoring."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor

MODEL_ID = "google/siglip-large-patch16-256"

STYLE_PROMPTS: Dict[str, str] = {
    "luxury": "a photo of luxury five-star hotel resort with elegant interior expensive decoration",
    "cozy": "a photo of cozy warm cafe interior with soft lighting comfortable chairs",
    "vibrant": "a photo of vibrant colorful street market festival crowded energetic",
    "minimal": "a photo of minimal white clean empty modern room simple design",
    "romantic": "a photo of romantic sunset couple candlelight dinner beautiful scenery",
    "adventurous": "a photo of adventurous mountain hiking rock climbing extreme outdoor activity",
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


def _siglip_style_scores(image: Image.Image) -> Dict[str, float]:
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


def _rule_based_scores(opencv_result: Optional[Mapping[str, float]]) -> Dict[str, float]:
    metrics = opencv_result or {}
    brightness = float(metrics.get("brightness", 0.5))
    saturation = float(metrics.get("saturation", 0.5))
    warm_tone = float(metrics.get("warm_tone", 0.5))
    contrast = float(metrics.get("contrast", 0.5))

    return {
        "vibrant": 1.0 if saturation > 0.6 and brightness > 0.6 else 0.1,
        "cozy": 1.0 if warm_tone > 0.6 and brightness > 0.5 else 0.1,
        "minimal": 1.0 if brightness > 0.7 and saturation < 0.4 else 0.1,
        "romantic": 1.0 if warm_tone > 0.7 and saturation > 0.5 else 0.1,
        "adventurous": 1.0 if contrast > 0.6 and saturation < 0.5 else 0.1,
        "luxury": 0.3,
    }


def analyze_style(
    image: Image.Image,
    opencv_result: Optional[Mapping[str, float]] = None,
) -> Dict[str, float]:
    """
    Score style via SigLIP zero-shot (60%) + OpenCV rules (40%), then softmax.

    Returns probabilities, e.g. {"luxury": 0.12, "cozy": 0.35, ...}.
    """
    siglip_scores = _siglip_style_scores(image)
    rule_scores = _rule_based_scores(opencv_result)

    combined = torch.tensor(
        [
            siglip_scores[name] * 0.6 + rule_scores[name] * 0.4
            for name in STYLE_NAMES
        ],
        dtype=torch.float32,
    )
    probs = torch.softmax(combined, dim=0)

    return {name: float(probs[i]) for i, name in enumerate(STYLE_NAMES)}
