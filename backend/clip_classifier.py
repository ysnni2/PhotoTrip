"""Fine-tuned SigLIP image classification (loads checkpoint from disk)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
from PIL import Image
from transformers import AutoModel, AutoProcessor

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "best_clip.pth"
_FALLBACK_MODEL_ID = "google/siglip-large-patch16-256"

_model: Optional["CLIPClassifier"] = None
_processor: Optional[Any] = None
_class_names: Optional[List[str]] = None
_torch_device: Optional[torch.device] = None


def _normalize_features(feats: Any) -> torch.Tensor:
    if not isinstance(feats, torch.Tensor):
        feats = feats.pooler_output
    return feats / feats.norm(dim=-1, keepdim=True)


def _image_features(model: nn.Module, pixel_values: torch.Tensor) -> torch.Tensor:
    feats = model.get_image_features(pixel_values=pixel_values)
    return _normalize_features(feats)


class CLIPClassifier(nn.Module):
    """SigLIP image encoder + linear head (matches clip_finetune checkpoint)."""

    def __init__(self, backbone: nn.Module, num_classes: int):
        super().__init__()
        self.clip = backbone
        self.head = nn.Linear(backbone.config.projection_dim, num_classes)

    def forward(self, pixel_values: torch.Tensor) -> torch.Tensor:
        emb = _image_features(self.clip, pixel_values)
        return self.head(emb)


def _resolve_checkpoint_path() -> Path:
    raw = os.environ.get("CLIP_MODEL_PATH", "").strip()
    if raw:
        return Path(raw)
    return DEFAULT_MODEL_PATH


def _get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_model() -> Tuple[CLIPClassifier, Any, List[str], torch.device]:
    global _model, _processor, _class_names, _torch_device

    if (
        _model is not None
        and _processor is not None
        and _class_names is not None
        and _torch_device is not None
    ):
        return _model, _processor, _class_names, _torch_device

    ckpt_path = _resolve_checkpoint_path()
    if not ckpt_path.is_file():
        raise FileNotFoundError(
            f"SigLIP checkpoint not found: {ckpt_path}. "
            "Set CLIP_MODEL_PATH or place weights at models/best_clip.pth"
        )

    device = _get_device()
    try:
        ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    except TypeError:
        ckpt = torch.load(ckpt_path, map_location=device)

    model_id = str(ckpt.get("model_id", _FALLBACK_MODEL_ID))
    class_names = list(ckpt["class_names"])
    if not class_names:
        raise ValueError("checkpoint class_names is empty")

    processor = AutoProcessor.from_pretrained(model_id)
    backbone = AutoModel.from_pretrained(model_id)
    model = CLIPClassifier(backbone, num_classes=len(class_names))
    model.clip.load_state_dict(ckpt["clip_state"])
    model.head.load_state_dict(ckpt["classifier_state"])
    model.to(device)
    model.eval()

    _model = model
    _processor = processor
    _class_names = class_names
    _torch_device = device
    return model, processor, class_names, device


def classify(image: Image.Image) -> Dict[str, float]:
    """
    Classify a PIL image with the fine-tuned SigLIP head.

    Returns per-class probabilities (softmax), keys lowercased from checkpoint class_names.
    Example: {"beach": 0.94, "nature": 0.02, "city": 0.01, ...}
    """
    model, processor, class_names, device = _load_model()
    if image.mode != "RGB":
        image = image.convert("RGB")

    batch = processor(images=image, return_tensors="pt")
    pixel_values = batch["pixel_values"].to(device)

    with torch.inference_mode():
        logits = model(pixel_values)
        probs = logits.softmax(dim=1)[0].cpu()

    return {
        str(name).lower(): float(probs[i])
        for i, name in enumerate(class_names)
    }
