"""CLIP pooler features + Lifestyle MLP heads (BCE multi-label)."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import torch
import torch.nn as nn
from PIL import Image

from .clip_base import load_clip

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"


class LifestyleMLP(nn.Module):
    def __init__(self, num_classes: int = 6, input_dim: int = 768) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.1),
            nn.Linear(512, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.1),
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def clip_pooler_features(image: Image.Image) -> torch.Tensor:
    if image.mode != "RGB":
        image = image.convert("RGB")
    model, processor = load_clip()
    device = next(model.parameters()).device
    batch = processor(images=image, return_tensors="pt")
    pixel_values = batch["pixel_values"].to(device)
    with torch.inference_mode():
        out = model.vision_model(pixel_values=pixel_values)
        return out.pooler_output.squeeze(0).cpu()


def _resolve_ckpt(name: str) -> Optional[Path]:
    for p in (MODELS_DIR / name, MODELS_DIR / "mlp_models" / name):
        if p.is_file():
            return p
    return None


def load_mlp_head(name: str, num_classes: int = 6) -> Optional[LifestyleMLP]:
    path = _resolve_ckpt(name)
    if path is None:
        return None
    head = LifestyleMLP(num_classes=num_classes)
    state = torch.load(path, map_location="cpu", weights_only=True)
    head.load_state_dict(state)
    head.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return head.to(device)


def mlp_multilabel_probs(head: nn.Module, pooler: torch.Tensor) -> torch.Tensor:
    device = next(head.parameters()).device
    with torch.inference_mode():
        logits = head(pooler.unsqueeze(0).to(device))
        return torch.sigmoid(logits).squeeze(0).cpu()
