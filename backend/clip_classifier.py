"""Fine-tuned CLIP image classification (loads checkpoint from disk)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from transformers import CLIPModel, CLIPProcessor

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "best_clip.pth"
_FALLBACK_MODEL_ID = "openai/clip-vit-base-patch32"

_IMAGE_SIZE = 224
_IMAGE_MEAN = (0.48145466, 0.4578275, 0.40821073)
_IMAGE_STD = (0.26862954, 0.26130258, 0.27577711)

_model: Optional["CLIPClassifier"] = None
_processor: Optional[CLIPProcessor] = None
_class_names: Optional[List[str]] = None
_torch_device: Optional[torch.device] = None


class CLIPClassifier(nn.Module):
    """CLIP image encoder + dropout linear head (matches clip_finetune checkpoint)."""

    def __init__(self, clip: CLIPModel, num_classes: int):
        super().__init__()
        self.clip = clip
        self.head = nn.Linear(clip.config.projection_dim, num_classes)

    def forward(self, pixel_values: torch.Tensor) -> torch.Tensor:
        emb = self.clip.get_image_features(pixel_values=pixel_values)
        if not isinstance(emb, torch.Tensor):
            emb = emb.pooler_output
        return self.head(emb)


def _resolve_checkpoint_path() -> Path:
    raw = os.environ.get("CLIP_MODEL_PATH", "").strip()
    if raw:
        return Path(raw)
    return DEFAULT_MODEL_PATH


def _get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _preprocess_image(image: Image.Image) -> torch.Tensor:
    """Same resize/normalize as classification/clip_finetune.py eval collate."""
    if image.mode != "RGB":
        image = image.convert("RGB")
    image = transforms.functional.resize(image, (_IMAGE_SIZE, _IMAGE_SIZE))
    tensor = transforms.functional.to_tensor(image)
    return transforms.functional.normalize(tensor, mean=_IMAGE_MEAN, std=_IMAGE_STD)


def _load_model() -> Tuple[CLIPClassifier, CLIPProcessor, List[str], torch.device]:
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
            f"CLIP checkpoint not found: {ckpt_path}. "
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

    processor = CLIPProcessor.from_pretrained(model_id)
    clip = CLIPModel.from_pretrained(model_id)
    model = CLIPClassifier(clip, num_classes=len(class_names))
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
    Classify a PIL image with the fine-tuned CLIP head.

    Returns per-class probabilities (softmax), keys lowercased from checkpoint class_names.
    Example: {"beach": 0.94, "nature": 0.02, "city": 0.01, ...}
    """
    model, _processor, class_names, device = _load_model()
    pixel_values = _preprocess_image(image).unsqueeze(0).to(device)

    with torch.inference_mode():
        logits = model(pixel_values)
        probs = logits.softmax(dim=1)[0].cpu()

    return {
        str(name).lower(): float(probs[i])
        for i, name in enumerate(class_names)
    }
