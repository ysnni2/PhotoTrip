"""ADE20K semantic segmentation with OneFormer (travel-related class ratios)."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Dict, Mapping, Optional, Tuple, Union

import numpy as np
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

_MASK_ALPHA = 160
_DEFAULT_MASK_COLOR = (200, 200, 200)

# ADE20K label id → RGB for colored overlay mask
_LABEL_RGB: Dict[int, Tuple[int, int, int]] = {
    120: (255, 165, 0),   # food — 주황
    17: (34, 139, 34),    # vegetation (plant) — 초록
    4: (34, 139, 34),     # tree
    9: (34, 139, 34),     # grass
    1: (128, 128, 128),   # building — 회색
    21: (30, 144, 255),   # water — 파랑
    26: (30, 144, 255),   # sea
    2: (135, 206, 235),   # sky — 하늘
    6: (105, 105, 105),   # road — 다크그레이
    46: (210, 180, 140),  # sand — 베이지
}

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


def segment_ratios(segment_result: Mapping[str, object]) -> Dict[str, float]:
    """Extract ratio dict from segment() output (supports legacy flat dict)."""
    ratios = segment_result.get("ratios")
    if isinstance(ratios, Mapping):
        return {str(k): float(v) for k, v in ratios.items()}
    return {str(k): float(v) for k, v in segment_result.items() if k != "mask_base64"}


def _ratios_from_pred(pred_2d: np.ndarray) -> Dict[str, float]:
    flat = pred_2d.reshape(-1)
    total = flat.size
    if total == 0:
        return {}

    out: Dict[str, float] = {}
    for name, label_id in _ADE_LABEL_IDS:
        if label_id is None:
            continue
        ratio = float((flat == label_id).sum() / total)
        if ratio > 0.0:
            out[name] = ratio
    return out


def _colored_mask_png_base64(pred_2d: np.ndarray) -> str:
    h, w = pred_2d.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 3] = _MASK_ALPHA

    for label_id in np.unique(pred_2d):
        lid = int(label_id)
        rgb = _LABEL_RGB.get(lid, _DEFAULT_MASK_COLOR)
        mask = pred_2d == label_id
        rgba[mask, 0] = rgb[0]
        rgba[mask, 1] = rgb[1]
        rgba[mask, 2] = rgb[2]

    buf = io.BytesIO()
    Image.fromarray(rgba, mode="RGBA").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def segment(image: Image.Image) -> Dict[str, object]:
    """
    Segment a PIL image and return pixel ratios plus a colored overlay mask (PNG base64).

    Returns:
        {
            "ratios": {"water": 0.12, "food": 0.41, ...},
            "mask_base64": "<PNG base64>",
        }
    """
    empty: Dict[str, object] = {"ratios": {}, "mask_base64": ""}
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
    if isinstance(pred, torch.Tensor):
        pred_2d = pred.cpu().numpy()
    else:
        pred_2d = np.asarray(pred)

    if pred_2d.size == 0:
        return empty

    ratios = _ratios_from_pred(pred_2d)
    mask_b64 = _colored_mask_png_base64(pred_2d)
    return {"ratios": ratios, "mask_base64": mask_b64}
