"""
Fine-tune OpenAI CLIP ViT-B/32 on folder-based image classification (Colab-friendly).

Expected layout:
  --train_dir (default /content/data/train): beach/, nature/, city/, food/, culture/
  --val_dir   (default /content/data/val):   beach/, nature/, city/, food/, culture/

Validation metrics and final evaluation (zero-shot, confusion matrix, test accuracy)
use the val split; there is no separate test folder.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score, confusion_matrix
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from transformers import CLIPModel, CLIPProcessor

try:
    from tqdm.auto import tqdm
except ImportError:  # pragma: no cover

    def tqdm(x, **kwargs):
        return x


MODEL_ID = "openai/clip-vit-base-patch32"
CLASS_NAMES = ["beach", "nature", "city", "indoor", "culture", "fashion", "food"]
ZERO_SHOT_TEMPLATES = [
    "a photo of {}",
    "a picture of {}",
    "an image of {}",
]


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _collect_samples(data_root: Path) -> Tuple[List[Path], List[int]]:
    paths: List[Path] = []
    labels: List[int] = []
    name_to_idx = {n: i for i, n in enumerate(CLASS_NAMES)}
    for name in CLASS_NAMES:
        d = data_root / name
        if not d.is_dir():
            continue
        idx = name_to_idx[name]
        for p in sorted(d.rglob("*")):
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
                paths.append(p)
                labels.append(idx)
    if not paths:
        raise FileNotFoundError(
            f"No images found under {data_root}. Expected subfolders: {CLASS_NAMES}"
        )
    return paths, labels


class PILDataset(Dataset):
    """Loads RGB PIL images; optional torchvision aug on PIL before collate resize/normalize."""

    def __init__(
        self,
        paths: Sequence[Path],
        labels: Sequence[int],
        aug: Optional[transforms.Compose],
    ):
        self.paths = list(paths)
        self.labels = list(labels)
        self.aug = aug

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, i: int):
        img = Image.open(self.paths[i]).convert("RGB")
        if self.aug is not None:
            img = self.aug(img)
        return img, self.labels[i]


class CLIPClassifier(nn.Module):
    """CLIP image tower + linear head on projection_dim."""

    def __init__(self, clip: CLIPModel, num_classes: int):
        super().__init__()
        self.clip = clip
        self.head = nn.Linear(clip.config.projection_dim, num_classes)

    def forward(self, pixel_values: torch.Tensor) -> torch.Tensor:
        emb = self.clip.get_image_features(pixel_values=pixel_values)
        if not isinstance(emb, torch.Tensor):
            emb = emb.pooler_output
        return self.head(emb)


@torch.inference_mode()
def zero_shot_accuracy(model, processor, loader, device):
    model.eval()
    class_texts = []
    for c in CLASS_NAMES:
        for t in ZERO_SHOT_TEMPLATES:
            class_texts.append(t.format(c))

    text_feats = []
    for i in range(0, len(class_texts), 32):
        tb = processor(text=class_texts[i : i + 32], return_tensors="pt", padding=True)
        tb = {k: v.to(device) for k, v in tb.items()}
        tf = model.get_text_features(**tb)
        if not isinstance(tf, torch.Tensor):
            tf = tf.pooler_output
        tf = tf / tf.norm(dim=-1, keepdim=True)
        text_feats.append(tf)

    text_feats = torch.cat(text_feats, dim=0)
    c, t = len(CLASS_NAMES), len(ZERO_SHOT_TEMPLATES)
    text_feats = text_feats.view(c, t, -1).mean(dim=1)
    text_feats = text_feats / text_feats.norm(dim=-1, keepdim=True)

    ys, ps = [], []
    for px, y in loader:
        px = px.to(device)
        imf = model.get_image_features(pixel_values=px)
        if not isinstance(imf, torch.Tensor):
            imf = imf.pooler_output
        imf = imf / imf.norm(dim=-1, keepdim=True)
        logits = imf @ text_feats.T * model.logit_scale.exp()
        pred = logits.argmax(dim=-1).cpu().numpy()
        ys.extend(y.numpy().tolist())
        ps.extend(pred.tolist())

    y_true = np.array(ys)
    y_pred = np.array(ps)
    return float(accuracy_score(y_true, y_pred)), y_true, y_pred


def train_one_epoch(
    model: CLIPClassifier,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scheduler: Optional[Any],
    device: torch.device,
    loss_fn: nn.Module,
) -> Tuple[float, float]:
    model.train()
    total_loss = 0.0
    correct = 0
    n = 0
    for pixel_values, labels in tqdm(loader, desc="train", leave=False):
        pixel_values = pixel_values.to(device)
        labels = labels.to(device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(pixel_values)
        loss = loss_fn(logits, labels)
        loss.backward()
        optimizer.step()
        if scheduler is not None:
            scheduler.step()
        bs = labels.size(0)
        total_loss += float(loss.item()) * bs
        correct += int((logits.argmax(dim=-1) == labels).sum().item())
        n += bs
    return total_loss / max(n, 1), correct / max(n, 1)


@torch.inference_mode()
def evaluate(
    model: CLIPClassifier,
    loader: DataLoader,
    device: torch.device,
    loss_fn: nn.Module,
) -> Tuple[float, float, np.ndarray, np.ndarray]:
    model.eval()
    total_loss = 0.0
    correct = 0
    n = 0
    ys: List[int] = []
    ps: List[int] = []
    for pixel_values, labels in tqdm(loader, desc="eval", leave=False):
        pixel_values = pixel_values.to(device)
        labels_dev = labels.to(device)
        logits = model(pixel_values)
        loss = loss_fn(logits, labels_dev)
        bs = labels.size(0)
        total_loss += float(loss.item()) * bs
        pred = logits.argmax(dim=-1)
        correct += int((pred == labels_dev).sum().item())
        n += bs
        ys.extend(labels.numpy().tolist())
        ps.extend(pred.cpu().numpy().tolist())
    y_true = np.array(ys)
    y_pred = np.array(ps)
    return total_loss / max(n, 1), correct / max(n, 1), y_true, y_pred


def plot_curves(
    history: Dict[str, List[float]],
    out_path: Path,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    epochs = range(1, len(history["train_loss"]) + 1)
    axes[0].plot(epochs, history["train_loss"], label="train")
    axes[0].plot(epochs, history["val_loss"], label="val")
    axes[0].set_xlabel("epoch")
    axes[0].set_ylabel("loss")
    axes[0].set_title("Loss")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(epochs, history["train_acc"], label="train acc")
    axes[1].plot(epochs, history["val_acc"], label="val acc")
    axes[1].set_xlabel("epoch")
    axes[1].set_ylabel("accuracy")
    axes[1].set_title("Accuracy")
    axes[1].set_ylim(0.0, 1.05)
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_confusion(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    out_path: Path,
    title: str = "Confusion matrix",
) -> None:
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(CLASS_NAMES))))
    fig, ax = plt.subplots(figsize=(6, 5))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=CLASS_NAMES)
    disp.plot(ax=ax, cmap="Blues", colorbar=False, values_format="d")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune CLIP on 5-class travel-style images.")
    parser.add_argument(
        "--train_dir",
        type=str,
        default="/content/data/train",
        help="Train root with subfolders beach, nature, city, food, culture",
    )
    parser.add_argument(
        "--val_dir",
        type=str,
        default="/content/data/val",
        help="Val root (same class subfolders); also used as the held-out eval / test set",
    )
    parser.add_argument("--output_dir", type=str, default="./clip_finetune_out")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument(
        "--num_workers",
        type=int,
        default=0 if sys.platform == "win32" else 2,
        help="DataLoader workers (0 recommended on Windows)",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    train_dir = Path(args.train_dir)
    val_dir = Path(args.val_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    device = _device()
    train_paths, train_labels = _collect_samples(train_dir)
    val_paths, val_labels = _collect_samples(val_dir)
    # No separate test split: reuse val paths/labels for zero-shot, fine-tuned eval, confusion matrix
    test_paths, test_labels = val_paths, val_labels

    processor = CLIPProcessor.from_pretrained(MODEL_ID)

    train_aug = transforms.Compose(
        [
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.05),
        ]
    )

    def make_collate(size: int, mean: Sequence[float], std: Sequence[float]):
        resize = transforms.Resize((size, size))

        def collate(batch):
            imgs, labs = zip(*batch)
            tensors = []
            for im in imgs:
                im = resize(im)
                tensors.append(transforms.functional.to_tensor(im))
            px = torch.stack(tensors)
            px = transforms.functional.normalize(px, mean=list(mean), std=list(std))
            return px, torch.tensor(labs, dtype=torch.long)

        return collate

    size = 224
    mean = [0.48145466, 0.4578275, 0.40821073]
    std = [0.26862954, 0.26130258, 0.27577711]

    train_ds = PILDataset(train_paths, train_labels, train_aug)
    val_ds = PILDataset(val_paths, val_labels, None)
    test_ds = PILDataset(test_paths, test_labels, None)

    collate_train = make_collate(size, mean, std)
    collate_eval = make_collate(size, mean, std)

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        collate_fn=collate_train,
        pin_memory=torch.cuda.is_available(),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        collate_fn=collate_eval,
        pin_memory=torch.cuda.is_available(),
    )
    test_loader = DataLoader(
        test_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        collate_fn=collate_eval,
        pin_memory=torch.cuda.is_available(),
    )

    base = CLIPModel.from_pretrained(MODEL_ID).to(device)
    # Zero-shot on test using frozen pretrained weights (copy before fine-tune)
    zs_acc, zs_y_true, zs_y_pred = zero_shot_accuracy(base, processor, test_loader, device)

    model = CLIPClassifier(base, num_classes=len(CLASS_NAMES)).to(device)
    for p in model.clip.text_model.parameters():
        p.requires_grad = False
    for p in model.clip.text_projection.parameters():
        p.requires_grad = False

    loss_fn = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=args.lr,
        weight_decay=0.01,
    )
    steps_per_epoch = max(len(train_loader), 1)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=args.epochs * steps_per_epoch,
    )

    history: Dict[str, List[float]] = {
        "train_loss": [],
        "val_loss": [],
        "train_acc": [],
        "val_acc": [],
    }
    best_val = -1.0
    best_path = out_dir / "best_clip.pth"

    for epoch in range(1, args.epochs + 1):
        tr_loss, tr_acc = train_one_epoch(
            model, train_loader, optimizer, scheduler, device, loss_fn
        )
        va_loss, va_acc, _, _ = evaluate(model, val_loader, device, loss_fn)
        history["train_loss"].append(tr_loss)
        history["val_loss"].append(va_loss)
        history["train_acc"].append(tr_acc)
        history["val_acc"].append(va_acc)
        print(
            f"Epoch {epoch}/{args.epochs} | "
            f"train_loss={tr_loss:.4f} train_acc={tr_acc:.4f} | "
            f"val_loss={va_loss:.4f} val_acc={va_acc:.4f}"
        )
        if va_acc > best_val:
            best_val = va_acc
            torch.save(
                {
                    "classifier_state": model.head.state_dict(),
                    "clip_state": model.clip.state_dict(),
                    "class_names": CLASS_NAMES,
                    "model_id": MODEL_ID,
                    "val_acc": best_val,
                },
                best_path,
            )

    plot_curves(history, out_dir / "training_curves.png")

    # Load best weights for test + confusion matrix
    try:
        ckpt = torch.load(best_path, map_location=device, weights_only=False)
    except TypeError:  # PyTorch < 2.4
        ckpt = torch.load(best_path, map_location=device)
    model.head.load_state_dict(ckpt["classifier_state"])
    model.clip.load_state_dict(ckpt["clip_state"])

    te_loss, te_acc, y_true, y_pred = evaluate(model, test_loader, device, loss_fn)
    print(f"Test (fine-tuned): loss={te_loss:.4f} acc={te_acc:.4f}")
    plot_confusion(
        zs_y_true,
        zs_y_pred,
        out_dir / "confusion_matrix_zeroshot.png",
        title="Zero-shot CLIP — test set",
    )
    plot_confusion(
        y_true,
        y_pred,
        out_dir / "confusion_matrix_finetuned.png",
        title="Fine-tuned CLIP — test set",
    )

    ft_acc = float(accuracy_score(y_true, y_pred))
    print("\n=== Zero-shot CLIP vs Fine-tuned CLIP (test set) ===")
    print(f"Zero-shot accuracy:  {zs_acc:.4f}")
    print(f"Fine-tuned accuracy: {ft_acc:.4f}")
    print(f"Δ (fine-tuned - zero-shot): {ft_acc - zs_acc:+.4f}")

    # Optional: per-class accuracy table
    print("\nPer-class (fine-tuned, test):")
    for i, name in enumerate(CLASS_NAMES):
        m = y_true == i
        if m.sum() == 0:
            continue
        acc_i = (y_pred[m] == y_true[m]).mean()
        print(f"  {name}: {float(acc_i):.4f} (n={int(m.sum())})")

    # Save comparison figure
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.bar(["zero-shot", "fine-tuned"], [zs_acc, ft_acc], color=["steelblue", "darkorange"])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("accuracy (test)")
    ax.set_title("CLIP: zero-shot vs fine-tuned")
    fig.tight_layout()
    fig.savefig(out_dir / "zeroshot_vs_finetuned.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
