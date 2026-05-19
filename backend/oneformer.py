"""ADE20K semantic segmentation with OneFormer (travel-related class ratios)."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import torch
from PIL import Image
from transformers import OneFormerForUniversalSegmentation, OneFormerProcessor

HF_MODEL_ID = "shi-labs/oneformer_ade20k_swin_large"
LOCAL_MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "oneformer_top"

# Backward-compatible alias (Hugging Face hub id)
MODEL_ID = HF_MODEL_ID

# ADE20K label ids (same mapping as previous Mask2Former backend)
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

_model: OneFormerForUniversalSegmentation | None = None
_processor: OneFormerProcessor | None = None


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _resolve_model_source() -> Union[str, Path]:
    """Use fine-tuned checkpoint under models/oneformer_top if present, else Hugging Face."""
    if LOCAL_MODEL_DIR.is_dir():
        return LOCAL_MODEL_DIR
    return HF_MODEL_ID


def _load_model() -> tuple[OneFormerForUniversalSegmentation, OneFormerProcessor]:
    global _model, _processor
    if _model is None or _processor is None:
        source = _resolve_model_source()
        _processor = OneFormerProcessor.from_pretrained(source)
        _model = OneFormerForUniversalSegmentation.from_pretrained(source).to(_device())
        _model.criterion.calculate_contrastive_loss = False
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

    inputs = processor(
        images=image,
        task_inputs=["semantic"],
        return_tensors="pt",
    )
    inputs = {
        k: v.to(device) if isinstance(v, torch.Tensor) else v
        for k, v in inputs.items()
    }

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
