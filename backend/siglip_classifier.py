"""Fine-tuned CLIP image classification (loads checkpoint from disk)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
from PIL import Image
from transformers import AutoModel, AutoProcessor

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "best_siglip.pth"
MODEL_ID = "openai/clip-vit-base-patch32"
_FALLBACK_MODEL_ID = MODEL_ID

CLASS_NAMES = ["beach", "nature", "city", "culture", "festival", "food"]

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
    """CLIP image encoder + linear head on projection_dim."""

    def __init__(self, backbone: nn.Module, num_classes: int):
        super().__init__()
        self.clip = backbone
        hidden_size = backbone.config.projection_dim
        self.head = nn.Linear(hidden_size, num_classes)

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


def _is_training_checkpoint(ckpt: Any) -> bool:
    return (
        isinstance(ckpt, dict)
        and "clip_state" in ckpt
        and "classifier_state" in ckpt
    )


def _is_full_state_dict(ckpt: Any) -> bool:
    if not isinstance(ckpt, dict):
        return False
    return any(
        str(k).startswith("clip.") or str(k).startswith("head.")
        for k in ckpt.keys()
    )


def inspect_checkpoint(ckpt_path: Optional[Path] = None) -> None:
    """Print checkpoint type/keys (run: python backend/siglip_classifier.py)."""
    path = ckpt_path or _resolve_checkpoint_path()
    print(f"path: {path}")
    print(f"exists: {path.is_file()}")
    if path.is_file():
        print(f"size_mb: {path.stat().st_size / 1024 / 1024:.2f}")

    try:
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        ckpt = torch.load(path, map_location="cpu")

    print(f"type: {type(ckpt)}")
    if not isinstance(ckpt, dict):
        return

    print(f"keys: {list(ckpt.keys())}")
    if _is_training_checkpoint(ckpt):
        print("format: training checkpoint (clip_state + classifier_state)")
        print(f"model_id: {ckpt.get('model_id')}")
        print(f"class_names: {ckpt.get('class_names')}")
        print(f"val_acc: {ckpt.get('val_acc')}")
    elif _is_full_state_dict(ckpt):
        sample = [k for k in ckpt.keys() if str(k).startswith(("clip.", "head."))][:5]
        print("format: flat model.state_dict()")
        print(f"sample keys: {sample}")
    else:
        print("format: unknown dict layout")


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
            f"CLIP checkpoint not found: {ckpt_path}. "
            "Set CLIP_MODEL_PATH or place weights at models/best_siglip.pth"
        )

    device = _get_device()
    try:
        ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    except TypeError:
        ckpt = torch.load(ckpt_path, map_location=device)

    if _is_training_checkpoint(ckpt):
        model_id = str(ckpt.get("model_id", _FALLBACK_MODEL_ID))
        class_names = list(ckpt.get("class_names") or CLASS_NAMES)
    elif _is_full_state_dict(ckpt):
        model_id = _FALLBACK_MODEL_ID
        class_names = list(CLASS_NAMES)
    else:
        raise ValueError(
            "Unsupported checkpoint format. Expected keys "
            "['clip_state', 'classifier_state', ...] or flat 'clip.*'/'head.*' state_dict. "
            "Run: python backend/siglip_classifier.py"
        )

    if not class_names:
        raise ValueError("checkpoint class_names is empty")

    processor = AutoProcessor.from_pretrained(model_id)
    backbone = AutoModel.from_pretrained(model_id)
    model = CLIPClassifier(backbone, num_classes=len(class_names))

    if _is_training_checkpoint(ckpt):
        model.clip.load_state_dict(ckpt["clip_state"])
        model.head.load_state_dict(ckpt["classifier_state"])
    else:
        model.load_state_dict(ckpt)

    model.to(device)
    model.eval()

    _model = model
    _processor = processor
    _class_names = class_names
    _torch_device = device
    return model, processor, class_names, device


def _probs_dict(logits: torch.Tensor, class_names: List[str]) -> Dict[str, float]:
    probs = logits.softmax(dim=1)[0].cpu()
    return {str(name).lower(): float(probs[i]) for i, name in enumerate(class_names)}


def classify(
    image: Image.Image,
    *,
    debug: Optional[bool] = None,
) -> Dict[str, float]:
    model, processor, class_names, device = _load_model()

    if image.mode != "RGB":
        image = image.convert("RGB")

    batch = processor(images=image, return_tensors="pt")
    pixel_values = batch["pixel_values"].to(device)

    if debug is None:
        debug = os.environ.get("SIGLIP_DEBUG_CLASSIFY", "").strip() in ("1", "true", "yes")

    with torch.inference_mode():
        logits = model(pixel_values)

        if debug:
            print("DEBUG pixel_values shape:", tuple(pixel_values.shape))
            print("DEBUG logits:", logits)
            print("DEBUG logits max:", logits.max().item())
            print("DEBUG logits min:", logits.min().item())
            print("DEBUG logits std:", logits.std().item())

            probs_normal = _probs_dict(logits, class_names)
            probs_temp = _probs_dict(logits * 5, class_names)
            print("DEBUG probs (softmax):", probs_normal)
            print("DEBUG probs (softmax, logits*5):", probs_temp)
            top_n = max(probs_normal, key=probs_normal.get)
            top_t = max(probs_temp, key=probs_temp.get)
            print(f"DEBUG top normal: {top_n}={probs_normal[top_n]:.4f}")
            print(f"DEBUG top temp*5: {top_t}={probs_temp[top_t]:.4f}")

        probs = logits.softmax(dim=1)[0].cpu()

    return {
        str(name).lower(): float(probs[i])
        for i, name in enumerate(class_names)
    }


if __name__ == "__main__":
    inspect_checkpoint()
