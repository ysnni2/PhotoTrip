"""ADE20K semantic segmentation with Mask2Former (travel-related class ratios)."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import torch
from PIL import Image
from transformers import AutoImageProcessor, Mask2FormerForUniversalSegmentation

MODEL_ID = "facebook/mask2former-swin-base-ade-semantic"

# ADE20K label ids for facebook/mask2former-swin-base-ade-semantic (id2label)
# "vegetation" → plant; snow has no ADE20K class in this checkpoint
_ADE_LABEL_IDS: Tuple[Tuple[str, Optional[int]], ...] = (
    ("water", 21),
    ("sky", 2),
    ("vegetation", 17),  # plant
    ("building", 1),
    ("road", 6),
    ("sand", 46),
    ("mountain", 16),
    ("sea", 26),
    ("tree", 4),
    ("grass", 9),
    ("rock", 34),
    ("snow", None),
    ("food", 120),
)

_model: Mask2FormerForUniversalSegmentation | None = None
_processor: AutoImageProcessor | None = None


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_model() -> tuple[Mask2FormerForUniversalSegmentation, AutoImageProcessor]:
    global _model, _processor
    if _model is None or _processor is None:
        _processor = AutoImageProcessor.from_pretrained(MODEL_ID)
        _model = Mask2FormerForUniversalSegmentation.from_pretrained(MODEL_ID).to(_device())
        _model.eval()
    return _model, _processor


def segment(image: Image.Image) -> Dict[str, float]:
    """
    Segment a PIL image and return pixel ratios for selected ADE20K travel classes.

    Each value is (pixels for that class) / (total pixels). Keys with ratio 0 are omitted.
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    model, processor = _load_model()
    device = next(model.parameters()).device

    inputs = processor(images=image, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.inference_mode():
        outputs = model(**inputs)

    h, w = image.size[1], image.size[0]
    seg_maps = processor.post_process_semantic_segmentation(
        outputs,
        target_sizes=[(h, w)],
    )
    pred = seg_maps[0]
    if not isinstance(pred, torch.Tensor):
        pred = torch.as_tensor(pred)
    pred = pred.view(-1)
    total = pred.numel()
    if total == 0:
        return {}

    out: Dict[str, float] = {}
    for name, label_id in _ADE_LABEL_IDS:
        if label_id is None:
            continue
        ratio = float((pred == label_id).sum().item() / total)
        if ratio > 0.0:
            out[name] = ratio

    return out
