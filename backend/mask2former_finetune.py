"""
Fine-tune Mask2Former on a unified travel-focused ADE20K label space.

Combines ADE20K (travel-class filter), Cityscapes, and FoodSeg103 with remapped masks.
Default paths target Kaggle; pass None to skip a source.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from transformers import AutoImageProcessor, Mask2FormerForUniversalSegmentation

try:
    from tqdm.auto import tqdm
except ImportError:  # pragma: no cover

    def tqdm(x, **kwargs):
        return x


MODEL_ID = "facebook/mask2former-swin-base-ade-semantic"
IGNORE_LABEL = 255

# ADE20K travel-related class ids (others → IGNORE_LABEL)
ADE_TRAVEL_IDS = frozenset({2, 4, 6, 9, 16, 17, 21, 26, 34, 46, 120})
ADE_TRAVEL_NAMES = {
    2: "sky",
    4: "tree",
    6: "road",
    9: "grass",
    16: "mountain",
    17: "plant",
    21: "water",
    26: "sea",
    34: "rock",
    46: "sand",
    120: "food",
}

# Cityscapes labelTrainIds → ADE20K id
_CITYSCAPES_TRAINID_TO_ADE: Dict[int, int] = {
    0: 6,   # road
    2: 1,   # building
    8: 17,  # vegetation
    10: 2,  # sky
    21: 21,  # water
}
CITYSCAPES_TO_ADE_LUT = np.full(256, IGNORE_LABEL, dtype=np.uint8)
for _cs_id, _ade_id in _CITYSCAPES_TRAINID_TO_ADE.items():
    CITYSCAPES_TO_ADE_LUT[_cs_id] = _ade_id

DEFAULT_ADE_ROOT = (
    "/kaggle/input/datasets/ipythonx/ade20k-scene-parsing/ADEChallengeData2016"
)
DEFAULT_CITYSCAPES_ROOT = "/kaggle/input/cityscapes/"
DEFAULT_FOODSEG_ROOT = "/kaggle/input/foodseg103/"

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


@dataclass(frozen=True)
class Sample:
    source: str
    image_path: Path
    mask_path: Path


def _exists_dir(path: Optional[str | Path]) -> bool:
    return path is not None and Path(path).is_dir()


def _mask_to_numpy(mask: Image.Image) -> np.ndarray:
    arr = np.array(mask)
    if arr.ndim == 3:
        arr = arr[:, :, 0]
    return arr.astype(np.int64)


def remap_ade_travel_mask(mask: np.ndarray) -> np.ndarray:
    """Keep only travel ADE ids; map everything else to IGNORE_LABEL."""
    out = np.full(mask.shape, IGNORE_LABEL, dtype=np.uint8)
    for ade_id in ADE_TRAVEL_IDS:
        out[mask == ade_id] = ade_id
    return out


def remap_cityscapes_mask(mask: np.ndarray) -> np.ndarray:
    """Map Cityscapes labelTrainIds to ADE ids via LUT."""
    clipped = np.clip(mask, 0, 255).astype(np.uint8)
    return CITYSCAPES_TO_ADE_LUT[clipped]


def remap_foodseg_mask(mask: np.ndarray) -> np.ndarray:
    """Map all FoodSeg103 ingredient ids (>0) to ADE food (120)."""
    out = np.full(mask.shape, IGNORE_LABEL, dtype=np.uint8)
    out[mask > 0] = 120
    return out


def _collect_ade20k(root: Path, split: str) -> List[Sample]:
    img_dir = root / "images" / split
    ann_dir = root / "annotations" / split
    if not img_dir.is_dir() or not ann_dir.is_dir():
        raise FileNotFoundError(
            f"ADE20K expected {img_dir} and {ann_dir}"
        )

    samples: List[Sample] = []
    for img_path in sorted(img_dir.iterdir()):
        if img_path.suffix.lower() not in _IMAGE_SUFFIXES:
            continue
        ann_path = ann_dir / f"{img_path.stem}.png"
        if ann_path.is_file():
            samples.append(Sample("ade20k", img_path, ann_path))
    if not samples:
        raise FileNotFoundError(f"No ADE20K pairs under {img_dir}")
    return samples


def _collect_cityscapes(root: Path, split: str) -> List[Sample]:
    # split: train | val
    img_root = root / "leftImg8bit" / split
    gt_root = root / "gtFine" / split
    if not img_root.is_dir() or not gt_root.is_dir():
        raise FileNotFoundError(
            f"Cityscapes expected {img_root} and {gt_root}"
        )

    samples: List[Sample] = []
    for img_path in sorted(img_root.rglob("*_leftImg8bit.png")):
        rel = img_path.relative_to(img_root)
        city = rel.parts[0]
        stem = img_path.name.replace("_leftImg8bit.png", "")
        ann_path = gt_root / city / f"{stem}_gtFine_labelTrainIds.png"
        if ann_path.is_file():
            samples.append(Sample("cityscapes", img_path, ann_path))
    if not samples:
        raise FileNotFoundError(f"No Cityscapes pairs under {img_root}")
    return samples


def _find_foodseg_dirs(root: Path) -> Tuple[Path, Path]:
    """Resolve image/mask roots for common FoodSeg103 layouts (zip / Kaggle)."""
    candidates = [
        (root / "FoodSeg103" / "Images", root / "FoodSeg103" / "Segmentation"),
        (root / "Images", root / "Segmentation"),
        (root / "foodseg103" / "Images", root / "foodseg103" / "Segmentation"),
        (root / "image", root / "mask"),
        (root / "images", root / "masks"),
    ]
    for img_dir, mask_dir in candidates:
        if img_dir.is_dir() and mask_dir.is_dir():
            return img_dir, mask_dir
    raise FileNotFoundError(
        f"FoodSeg103 Images/Segmentation not found under {root}. "
        f"Tried: {[str(c[0].parent) for c in candidates]}"
    )


def _collect_foodseg103(root: Path) -> List[Sample]:
    img_dir, mask_dir = _find_foodseg_dirs(root)

    samples: List[Sample] = []
    for img_path in sorted(img_dir.rglob("*")):
        if img_path.suffix.lower() not in _IMAGE_SUFFIXES:
            continue
        rel = img_path.relative_to(img_dir)
        mask_path = mask_dir / rel
        if not mask_path.is_file():
            mask_path = mask_dir / f"{img_path.stem}.png"
        if mask_path.is_file():
            samples.append(Sample("foodseg103", img_path, mask_path))
    if not samples:
        raise FileNotFoundError(f"No FoodSeg103 pairs under {img_dir}")
    return samples


def build_unified_samples(
    ade_root: Optional[str | Path] = None,
    cityscapes_root: Optional[str | Path] = None,
    foodseg_root: Optional[str | Path] = None,
    ade_split: str = "training",
    cityscapes_split: str = "train",
) -> List[Sample]:
    """Collect (source, image, mask) paths from all configured datasets."""
    samples: List[Sample] = []

    if _exists_dir(ade_root):
        samples.extend(_collect_ade20k(Path(ade_root), ade_split))
        print(f"  ADE20K ({ade_split}): {sum(1 for s in samples if s.source == 'ade20k')} images")
    else:
        print(f"  ADE20K: skipped ({ade_root})")

    n_before = len(samples)
    if _exists_dir(cityscapes_root):
        cs = _collect_cityscapes(Path(cityscapes_root), cityscapes_split)
        samples.extend(cs)
        print(f"  Cityscapes ({cityscapes_split}): {len(cs)} images")
    else:
        print(f"  Cityscapes: skipped ({cityscapes_root})")

    if _exists_dir(foodseg_root):
        fs = _collect_foodseg103(Path(foodseg_root))
        samples.extend(fs)
        print(f"  FoodSeg103: {len(fs)} images")
    else:
        print(f"  FoodSeg103: skipped ({foodseg_root})")

    if not samples:
        raise RuntimeError("No samples collected; check dataset paths.")
    print(f"  Total unified samples: {len(samples)}")
    return samples


class UnifiedTravelDataset(Dataset):
    """
    Merges ADE20K, Cityscapes, and FoodSeg103 into one ADE20K-id mask space.

    Each __getitem__ returns processor-ready tensors (pixel_values, labels, …).
    """

    def __init__(
        self,
        samples: Sequence[Sample],
        processor: AutoImageProcessor,
    ):
        self.samples = list(samples)
        self.processor = processor

    def __len__(self) -> int:
        return len(self.samples)

    def _load_remapped_mask(self, sample: Sample) -> np.ndarray:
        mask_img = Image.open(sample.mask_path)
        mask = _mask_to_numpy(mask_img)

        if sample.source == "ade20k":
            return remap_ade_travel_mask(mask)
        if sample.source == "cityscapes":
            return remap_cityscapes_mask(mask)
        if sample.source == "foodseg103":
            return remap_foodseg_mask(mask)
        raise ValueError(f"Unknown source: {sample.source}")

    def __getitem__(self, index: int) -> Dict[str, torch.Tensor]:
        sample = self.samples[index]
        image = Image.open(sample.image_path).convert("RGB")
        seg_map = self._load_remapped_mask(sample)

        encoded = self.processor(
            images=image,
            segmentation_maps=seg_map,
            return_tensors="pt",
        )
        return {k: v.squeeze(0) for k, v in encoded.items()}


def collate_batch(
    batch: List[Dict[str, torch.Tensor]],
    *,
    ignore_index: int = IGNORE_LABEL,
) -> Dict[str, torch.Tensor]:
    pixel_values = torch.stack([b["pixel_values"] for b in batch])
    mask_labels = [b["mask_labels"] for b in batch]
    max_h = max(m.shape[-2] for m in mask_labels)
    max_w = max(m.shape[-1] for m in mask_labels)

    padded_masks = []
    for m in mask_labels:
        _, h, w = m.shape
        pad = torch.full(
            (1, max_h, max_w),
            fill_value=ignore_index,
            dtype=m.dtype,
        )
        pad[:, :h, :w] = m
        padded_masks.append(pad)

    return {
        "pixel_values": pixel_values,
        "mask_labels": torch.stack(padded_masks),
        "class_labels": [b["class_labels"] for b in batch],
    }


def train_one_epoch(
    model: Mask2FormerForUniversalSegmentation,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    *,
    epoch: int,
    grad_accum: int = 1,
) -> float:
    model.train()
    total_loss = 0.0
    n_steps = 0
    optimizer.zero_grad(set_to_none=True)

    pbar = tqdm(loader, desc=f"epoch {epoch}", leave=False)
    for step, batch in enumerate(pbar):
        pixel_values = batch["pixel_values"].to(device)
        mask_labels = batch["mask_labels"].to(device)
        class_labels = [
            [lbl.to(device) for lbl in labels] for labels in batch["class_labels"]
        ]

        outputs = model(
            pixel_values=pixel_values,
            mask_labels=mask_labels,
            class_labels=class_labels,
        )
        loss = outputs.loss / grad_accum
        loss.backward()

        if (step + 1) % grad_accum == 0 or (step + 1) == len(loader):
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)

        total_loss += float(outputs.loss.detach())
        n_steps += 1
        pbar.set_postfix(loss=f"{outputs.loss.item():.4f}")

    return total_loss / max(n_steps, 1)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fine-tune Mask2Former on unified travel data")
    p.add_argument("--ade-root", type=str, default=DEFAULT_ADE_ROOT)
    p.add_argument("--cityscapes-root", type=str, default=DEFAULT_CITYSCAPES_ROOT)
    p.add_argument("--foodseg-root", type=str, default=DEFAULT_FOODSEG_ROOT)
    p.add_argument("--ade-split", type=str, default="training", choices=("training", "validation"))
    p.add_argument("--cityscapes-split", type=str, default="train", choices=("train", "val"))
    p.add_argument("--output-dir", type=str, default="/kaggle/working/mask2former_travel")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=2)
    p.add_argument("--lr", type=float, default=5e-5)
    p.add_argument("--num-workers", type=int, default=2)
    p.add_argument("--grad-accum", type=int, default=4)
    p.add_argument("--max-samples", type=int, default=0, help="0 = use all")
    p.add_argument("--save-every", type=int, default=1)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("Collecting unified dataset samples...")
    samples = build_unified_samples(
        ade_root=args.ade_root,
        cityscapes_root=args.cityscapes_root,
        foodseg_root=args.foodseg_root,
        ade_split=args.ade_split,
        cityscapes_split=args.cityscapes_split,
    )
    if args.max_samples > 0:
        samples = samples[: args.max_samples]
        print(f"  Subsampled to {len(samples)} for debugging")

    processor = AutoImageProcessor.from_pretrained(MODEL_ID)
    dataset = UnifiedTravelDataset(samples, processor)
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        collate_fn=collate_batch,
        pin_memory=device.type == "cuda",
    )

    model = Mask2FormerForUniversalSegmentation.from_pretrained(MODEL_ID)
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        avg_loss = train_one_epoch(
            model,
            loader,
            optimizer,
            device,
            epoch=epoch,
            grad_accum=args.grad_accum,
        )
        print(f"Epoch {epoch}/{args.epochs} — avg loss: {avg_loss:.4f}")

        if epoch % args.save_every == 0:
            ckpt_dir = out_dir / f"epoch_{epoch}"
            model.save_pretrained(ckpt_dir)
            processor.save_pretrained(ckpt_dir)
            print(f"  Saved → {ckpt_dir}")

    final_dir = out_dir / "final"
    model.save_pretrained(final_dir)
    processor.save_pretrained(final_dir)
    print(f"Done. Final checkpoint: {final_dir}")


if __name__ == "__main__":
    main()
