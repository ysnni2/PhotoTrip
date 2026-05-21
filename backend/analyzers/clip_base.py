"""Shared CLIP zero-shot utilities for lifestyle analyzers."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import torch
import torch.nn as nn
from PIL import Image
from transformers import AutoModel, AutoProcessor

CLIP_MODEL_ID = "openai/clip-vit-base-patch32"

_clip_model: Optional[nn.Module] = None
_clip_processor: Optional[Any] = None
_text_features_cache: Dict[str, torch.Tensor] = {}


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _normalize_features(feats: Any) -> torch.Tensor:
    if not isinstance(feats, torch.Tensor):
        feats = feats.pooler_output
    return feats / feats.norm(dim=-1, keepdim=True)


def _image_features(model: nn.Module, pixel_values: torch.Tensor) -> torch.Tensor:
    feats = model.get_image_features(pixel_values=pixel_values)
    return _normalize_features(feats)


def _text_features(model: nn.Module, text_batch: Dict[str, torch.Tensor]) -> torch.Tensor:
    feats = model.get_text_features(**text_batch)
    return _normalize_features(feats)


def _zeroshot_logits(
    model: nn.Module,
    image_feats: torch.Tensor,
    text_feats: torch.Tensor,
) -> torch.Tensor:
    return image_feats @ text_feats.T * model.logit_scale.exp()


def load_clip() -> Tuple[nn.Module, Any]:
    global _clip_model, _clip_processor
    if _clip_model is None or _clip_processor is None:
        _clip_processor = AutoProcessor.from_pretrained(CLIP_MODEL_ID)
        _clip_model = AutoModel.from_pretrained(CLIP_MODEL_ID).to(_device())
        _clip_model.eval()
    return _clip_model, _clip_processor


def _prompts_for_label(prompt_map: Mapping[str, Union[str, Sequence[str]]], label: str) -> List[str]:
    raw = prompt_map[label]
    return [raw] if isinstance(raw, str) else list(raw)


def encode_text_bank(
    model: nn.Module,
    processor: Any,
    labels: Sequence[str],
    prompts: Mapping[str, Union[str, Sequence[str]]],
    cache_key: str,
) -> torch.Tensor:
    if cache_key in _text_features_cache:
        return _text_features_cache[cache_key]

    device = next(model.parameters()).device
    rows: List[torch.Tensor] = []
    for label in labels:
        texts = _prompts_for_label(prompts, label)
        batch = processor(text=texts, return_tensors="pt", padding=True)
        batch = {k: v.to(device) for k, v in batch.items()}
        with torch.inference_mode():
            feats = _text_features(model, batch)
        rows.append(feats.mean(dim=0, keepdim=True))
    bank = torch.cat(rows, dim=0)
    _text_features_cache[cache_key] = bank
    return bank


def clip_zero_shot_scores(
    image: Image.Image,
    labels: Sequence[str],
    prompts: Mapping[str, Union[str, Sequence[str]]],
    cache_key: str,
) -> Dict[str, float]:
    """Return softmax probabilities over ``labels`` for one image."""
    if image.mode != "RGB":
        image = image.convert("RGB")

    model, processor = load_clip()
    device = next(model.parameters()).device

    text_feats = encode_text_bank(model, processor, labels, prompts, cache_key)

    img_batch = processor(images=image, return_tensors="pt")
    pixel_values = img_batch["pixel_values"].to(device)
    with torch.inference_mode():
        image_feats = _image_features(model, pixel_values)
        logits = _zeroshot_logits(model, image_feats, text_feats)
        probs = logits.softmax(dim=-1)[0].cpu()

    return {label: float(probs[i]) for i, label in enumerate(labels)}
