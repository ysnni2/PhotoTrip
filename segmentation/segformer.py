"""ADE20K semantic segmentation with NVIDIA SegFormer B0 (512)."""

from __future__ import annotations

from typing import Dict

import torch
from PIL import Image
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

MODEL_ID = "nvidia/segformer-b0-finetuned-ade-512-512"

# ADE20K class ids (Hugging Face / ADE20K index scheme for this checkpoint)
_ADE_TARGETS: tuple[tuple[str, int], ...] = (
    ("water", 21),
    ("sky", 2),
    ("vegetation", 4),
    ("building", 1),
    ("road", 6),
    ("sand", 46),
)

_model: SegformerForSemanticSegmentation | None = None
_processor: SegformerImageProcessor | None = None


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_model() -> tuple[SegformerForSemanticSegmentation, SegformerImageProcessor]:
    global _model, _processor
    if _model is None or _processor is None:
        _processor = SegformerImageProcessor.from_pretrained(MODEL_ID)
        _model = SegformerForSemanticSegmentation.from_pretrained(MODEL_ID).to(_device())
        _model.eval()
    return _model, _processor


def segment(image: Image.Image) -> Dict[str, float]:
    """
    Segment a PIL image with ADE20K SegFormer and return pixel ratios for selected classes.

    Each value is (pixels predicted as that class) / (total pixels in the original image).
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    model, processor = _load_model()
    device = next(model.parameters()).device

    inputs = processor(images=image, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.inference_mode():
        outputs = model(**inputs)

    # Map logits to original (H, W) so ratios match the input PIL image
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
        return {name: 0.0 for name, _ in _ADE_TARGETS}

    return {
        name: float((pred == label_id).sum().item() / total)
        for name, label_id in _ADE_TARGETS
    }
