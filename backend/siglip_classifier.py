"""Fine-tuned CLIP image classification with TTA + Temperature Scaling."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms as T
from transformers import AutoModel, AutoProcessor

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "best_clip.pth"
MODEL_ID = "openai/clip-vit-base-patch32"
_FALLBACK_MODEL_ID = MODEL_ID

CLASS_NAMES = ["beach", "nature", "city", "culture", "festival", "food"]

# Low confidence or tight top-2 margin → treat as "other" and ask Gemini for a travel hint
OTHER_CONF_THRESHOLD = 0.35
OTHER_MARGIN_THRESHOLD = 0.08

# ── Temperature Scaling ───────────────────────────────────────────────────────
# 1.0 = 원본, >1.0 = softer (오버피팅된 confidence 낮춰 보정)
# train 98.8% vs val 93.5% 갭 고려 → 1.1
TEMPERATURE: float = 1.1

# ── TTA 설정 ──────────────────────────────────────────────────────────────────
TTA_ENABLED: bool = True
TTA_RUNS: int = 6

_model: Optional["CLIPClassifier"] = None
_processor: Optional[Any] = None
_class_names: Optional[List[str]] = None
_torch_device: Optional[torch.device] = None

_CLIP_MEAN = [0.48145466, 0.4578275, 0.40821073]
_CLIP_STD  = [0.26862954, 0.26130258, 0.27577711]
_IMG_SIZE  = 224


def _normalize_features(feats: Any) -> torch.Tensor:
    if not isinstance(feats, torch.Tensor):
        feats = feats.pooler_output
    return feats / feats.norm(dim=-1, keepdim=True)


def _image_features(model: nn.Module, pixel_values: torch.Tensor) -> torch.Tensor:
    feats = model.get_image_features(pixel_values=pixel_values)
    return _normalize_features(feats)


class CLIPClassifier(nn.Module):
    def __init__(self, backbone: nn.Module, num_classes: int):
        super().__init__()
        self.clip = backbone
        hidden_size = (
            backbone.config.projection_dim
            if hasattr(backbone.config, "projection_dim")
            else backbone.config.vision_config.hidden_size
            if hasattr(backbone.config, "vision_config")
            else backbone.config.hidden_size
        )
        self.head = nn.Linear(hidden_size, num_classes)

    def forward(self, pixel_values: torch.Tensor) -> torch.Tensor:
        emb = _image_features(self.clip, pixel_values)
        return self.head(emb)


# ── TTA Transforms ────────────────────────────────────────────────────────────
def _base_transform() -> T.Compose:
    return T.Compose([
        T.Resize((_IMG_SIZE, _IMG_SIZE)),
        T.ToTensor(),
        T.Normalize(mean=_CLIP_MEAN, std=_CLIP_STD),
    ])


def _tta_transforms() -> List[T.Compose]:
    """일상 사진 특성 고려 → 과도한 변형 지양."""
    return [
        # 1) 기본
        T.Compose([
            T.Resize((_IMG_SIZE, _IMG_SIZE)),
            T.ToTensor(),
            T.Normalize(mean=_CLIP_MEAN, std=_CLIP_STD),
        ]),
        # 2) 좌우 반전
        T.Compose([
            T.Resize((_IMG_SIZE, _IMG_SIZE)),
            T.RandomHorizontalFlip(p=1.0),
            T.ToTensor(),
            T.Normalize(mean=_CLIP_MEAN, std=_CLIP_STD),
        ]),
        # 3) 약간 확대 후 center crop
        T.Compose([
            T.Resize(int(_IMG_SIZE * 1.1)),
            T.CenterCrop(_IMG_SIZE),
            T.ToTensor(),
            T.Normalize(mean=_CLIP_MEAN, std=_CLIP_STD),
        ]),
        # 4) 밝기/대비 조정 (일상 사진 조명 변화 대응)
        T.Compose([
            T.Resize((_IMG_SIZE, _IMG_SIZE)),
            T.ColorJitter(brightness=0.1, contrast=0.1),
            T.ToTensor(),
            T.Normalize(mean=_CLIP_MEAN, std=_CLIP_STD),
        ]),
        # 5) 좌우 반전 + 확대
        T.Compose([
            T.Resize(int(_IMG_SIZE * 1.1)),
            T.CenterCrop(_IMG_SIZE),
            T.RandomHorizontalFlip(p=1.0),
            T.ToTensor(),
            T.Normalize(mean=_CLIP_MEAN, std=_CLIP_STD),
        ]),
        # 6) 살짝 어둡게 (역광 사진 대응)
        T.Compose([
            T.Resize((_IMG_SIZE, _IMG_SIZE)),
            T.ColorJitter(brightness=(0.7, 0.85)),
            T.ToTensor(),
            T.Normalize(mean=_CLIP_MEAN, std=_CLIP_STD),
        ]),
    ]


# ── 기존 코드와 동일한 부분 (생략 없이 전부) ──────────────────────────────────
def _resolve_checkpoint_path() -> Path:
    raw = os.environ.get("CLIP_MODEL_PATH", "").strip()
    if raw:
        return Path(raw)
    return DEFAULT_MODEL_PATH


def _get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _is_training_checkpoint(ckpt: Any) -> bool:
    return isinstance(ckpt, dict) and "clip_state" in ckpt and "classifier_state" in ckpt


def _is_full_state_dict(ckpt: Any) -> bool:
    if not isinstance(ckpt, dict):
        return False
    return any(str(k).startswith("clip.") or str(k).startswith("head.") for k in ckpt.keys())


def inspect_checkpoint(ckpt_path: Optional[Path] = None) -> None:
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
        print("format: training checkpoint")
        print(f"class_names: {ckpt.get('class_names')}")
        print(f"val_acc: {ckpt.get('val_acc')}")


def _load_model() -> Tuple[CLIPClassifier, Any, List[str], torch.device]:
    global _model, _processor, _class_names, _torch_device
    if _model is not None and _processor is not None and _class_names is not None and _torch_device is not None:
        return _model, _processor, _class_names, _torch_device

    ckpt_path = _resolve_checkpoint_path()
    if not ckpt_path.is_file():
        raise FileNotFoundError(f"CLIP checkpoint not found: {ckpt_path}.")

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
        raise ValueError("Unsupported checkpoint format.")

    processor = AutoProcessor.from_pretrained(model_id, use_fast=False)
    backbone = AutoModel.from_pretrained(model_id)
    model = CLIPClassifier(backbone, num_classes=len(class_names))

    if _is_training_checkpoint(ckpt):
        model.clip.load_state_dict(ckpt["clip_state"])
        model.head.load_state_dict(ckpt["classifier_state"])
    else:
        model.load_state_dict(ckpt)

    model.to(device)
    model.eval()
    _model, _processor, _class_names, _torch_device = model, processor, class_names, device
    return model, processor, class_names, device


# ── 핵심 변경: classify() ─────────────────────────────────────────────────────
def classify(
    image: Image.Image,
    *,
    use_tta: bool = True,
    temperature: float = 1.1,
    debug: bool = False,
) -> Dict[str, float]:
    model, _, class_names, device = _load_model()
    if image.mode != "RGB":
        image = image.convert("RGB")

    if use_tta:
        logits_list = []
        for i, tfm in enumerate(_tta_transforms()[:TTA_RUNS]):
            pixel_values = tfm(image).unsqueeze(0).to(device)
            with torch.inference_mode():
                logits = model(pixel_values)
            logits_list.append(logits)

            if debug:
                probs_i = (logits / temperature).softmax(dim=1)[0].cpu()
                top = max(class_names, key=lambda n: probs_i[class_names.index(n)])
                print(f"  TTA run {i+1}: {top} ({probs_i[class_names.index(top)]:.3f})")

        # logit 평균 → temperature scaling → softmax
        avg_logits = torch.stack(logits_list, dim=0).mean(dim=0)
        probs = (avg_logits / temperature).softmax(dim=1)[0].cpu()

    else:
        pixel_values = _base_transform()(image).unsqueeze(0).to(device)
        with torch.inference_mode():
            logits = model(pixel_values)
        probs = (logits / temperature).softmax(dim=1)[0].cpu()

    return {str(name).lower(): float(probs[i]) for i, name in enumerate(class_names)}


def classify_with_fallback(
    image: Image.Image,
    *,
    use_tta: bool = True,
    temperature: float = 1.1,
    debug: bool = False,
) -> Dict[str, Any]:
    """
    SigLIP classify; when confidence is low (is_other), enrich with Gemini travel hint.
    """
    scores = classify(
        image, use_tta=use_tta, temperature=temperature, debug=debug
    )
    all_scores = {str(name).lower(): float(scores.get(name, 0.0)) for name in CLASS_NAMES}
    if not all_scores:
        return {
            "category": "",
            "confidence": 0.0,
            "all_scores": {},
            "is_other": True,
            "other_hint": None,
            "travel_hint": None,
            "hint_weight": 0.0,
        }

    category = max(all_scores, key=all_scores.get)
    confidence = all_scores[category]
    sorted_probs = sorted(all_scores.values(), reverse=True)
    margin = (
        sorted_probs[0] - sorted_probs[1] if len(sorted_probs) > 1 else 1.0
    )
    is_other = (
        confidence < OTHER_CONF_THRESHOLD
        or margin < OTHER_MARGIN_THRESHOLD
    )

    other_hint = None
    travel_hint = None
    hint_weight = 0.0
    if is_other:
        from analyzers.other_analyzer import analyze_other_as_travel_hint

        other_hint = analyze_other_as_travel_hint(image)
        travel_hint = other_hint.get("travel_hint")
        hint_weight = float(other_hint.get("hint_weight", 0.3))

    return {
        "category": category,
        "confidence": confidence,
        "all_scores": all_scores,
        "is_other": is_other,
        "other_hint": other_hint,
        "travel_hint": travel_hint,
        "hint_weight": hint_weight,
    }


def tune_temperature(
    val_images: List[Image.Image],
    val_labels: List[int],
    candidates: List[float] = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 2.0],
) -> float:
    """val set으로 최적 temperature 탐색 (재학습 불필요)."""
    model, _, class_names, device = _load_model()
    tfm = _base_transform()
    all_logits = []
    for img in val_images:
        if img.mode != "RGB":
            img = img.convert("RGB")
        pv = tfm(img).unsqueeze(0).to(device)
        with torch.inference_mode():
            all_logits.append(model(pv).cpu())

    all_logits = torch.cat(all_logits, dim=0)
    labels_tensor = torch.tensor(val_labels, dtype=torch.long)
    criterion = nn.CrossEntropyLoss()

    best_t, best_nll = 1.0, float("inf")
    for t in candidates:
        nll = criterion(all_logits / t, labels_tensor).item()
        print(f"  temperature={t:.1f} → NLL={nll:.4f}")
        if nll < best_nll:
            best_nll, best_t = nll, t

    print(f"\n✅ 최적 temperature: {best_t} → TEMPERATURE = {best_t} 로 업데이트")
    return best_t


if __name__ == "__main__":
    inspect_checkpoint()