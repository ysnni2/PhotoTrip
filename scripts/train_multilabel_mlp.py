"""
BCE multi-label MLP trainer (place + mood heads on CLIP pooler).

Input: multilabel_dataset_v3.pt (or multilabel_dataset.pt)
Output: models/mlp_place_best.pth, models/mlp_mood_best.pth, training_report.json

Style head (--train-style): BCEWithLogitsLoss + pos_weight (max 10) + rare-label sampler.
Default: place/mood only — run style training after checking v3 distribution.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from analyzers.mlp_head import LifestyleMLP  # noqa: E402
from analyzers.multilabel_utils import compute_pos_weight, make_rare_label_sampler  # noqa: E402

KAGGLE_WORKING = Path("/kaggle/working")
MODELS_DIR = _ROOT / "models"


def _metrics(logits: torch.Tensor, targets: torch.Tensor, threshold: float = 0.5) -> Dict[str, float]:
    probs = torch.sigmoid(logits)
    pred = (probs >= threshold).float()
    tp = (pred * targets).sum()
    fp = (pred * (1 - targets)).sum()
    fn = ((1 - pred) * targets).sum()
    precision = float(tp / (tp + fp + 1e-8))
    recall = float(tp / (tp + fn + 1e-8))
    f1 = float(2 * precision * recall / (precision + recall + 1e-8))
    exact = float((pred == targets).all(dim=1).float().mean())
    return {"precision": precision, "recall": recall, "f1": f1, "subset_acc": exact}


def train_head(
    name: str,
    X_train: torch.Tensor,
    y_train: torch.Tensor,
    X_val: torch.Tensor,
    y_val: torch.Tensor,
    *,
    epochs: int = 25,
    batch_size: int = 32,
    lr: float = 1e-3,
    pos_weight: Optional[torch.Tensor] = None,
    weighted_sampler: Optional[Any] = None,
) -> Tuple[LifestyleMLP, Dict[str, float]]:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LifestyleMLP(num_classes=y_train.shape[1]).to(device)
    if pos_weight is not None:
        criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight.to(device))
    else:
        criterion = nn.BCEWithLogitsLoss()
    optim = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)

    train_ds = TensorDataset(X_train, y_train)
    if weighted_sampler is not None:
        train_loader = DataLoader(
            train_ds, batch_size=batch_size, sampler=weighted_sampler
        )
    else:
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

    best_f1 = -1.0
    best_state = None
    history = []

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optim.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optim.step()
            total_loss += float(loss.item()) * xb.size(0)

        model.eval()
        with torch.inference_mode():
            val_logits = model(X_val.to(device))
            val_metrics = _metrics(val_logits, y_val.to(device))
        val_metrics["loss"] = float(criterion(val_logits, y_val.to(device)).item())
        val_metrics["epoch"] = epoch
        val_metrics["train_loss"] = total_loss / max(len(train_loader.dataset), 1)
        history.append(val_metrics)

        if val_metrics["f1"] > best_f1:
            best_f1 = val_metrics["f1"]
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        print(f"[{name}] epoch {epoch:02d}  val_f1={val_metrics['f1']:.4f}  loss={val_metrics['loss']:.4f}")

    if best_state:
        model.load_state_dict(best_state)
    return model, {"best_f1": best_f1, "history": history}


def main() -> None:
    p = argparse.ArgumentParser()
    default_data = KAGGLE_WORKING / "multilabel_dataset_v3.pt"
    if not default_data.is_file():
        default_data = _ROOT / "outputs" / "multilabel_dataset_v3.pt"
    if not default_data.is_file():
        default_data = _ROOT / "outputs" / "multilabel_dataset.pt"
    p.add_argument("--dataset", type=str, default=str(default_data))
    p.add_argument("--epochs", type=int, default=25)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument(
        "--train-style",
        action="store_true",
        help="Train style head (off by default; check v3 distribution first)",
    )
    p.add_argument("--cozy-mult", type=float, default=4.0)
    p.add_argument("--romantic-calm-mult", type=float, default=2.5)
    args = p.parse_args()

    data = torch.load(args.dataset, map_location="cpu", weights_only=False)
    X_train, y_place_train, y_mood_train = (
        data["train"]["X"],
        data["train"]["y_place"],
        data["train"]["y_mood"],
    )
    X_val, y_place_val, y_mood_val = data["val"]["X"], data["val"]["y_place"], data["val"]["y_mood"]

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    mlp_dir = MODELS_DIR / "mlp_models"
    mlp_dir.mkdir(exist_ok=True)

    place_model, place_rep = train_head(
        "place", X_train, y_place_train, X_val, y_place_val, epochs=args.epochs, batch_size=args.batch_size
    )
    mood_model, mood_rep = train_head(
        "mood", X_train, y_mood_train, X_val, y_mood_val, epochs=args.epochs, batch_size=args.batch_size
    )

    torch.save(place_model.state_dict(), mlp_dir / "mlp_place_best.pth")
    torch.save(mood_model.state_dict(), MODELS_DIR / "mlp_place_best.pth")
    torch.save(mood_model.state_dict(), mlp_dir / "mlp_mood_best.pth")
    torch.save(mood_model.state_dict(), MODELS_DIR / "mlp_mood_best.pth")

    report: Dict[str, Any] = {"place": place_rep, "mood": mood_rep, "style": None}

    if args.train_style and "y_style" in data["train"]:
        y_style_train = data["train"]["y_style"]
        y_style_val = data["val"]["y_style"]
        pw = data.get("style_pos_weight")
        if pw is None:
            pw = compute_pos_weight(y_style_train)
        sampler = make_rare_label_sampler(
            y_style_train,
            cozy_mult=args.cozy_mult,
            romantic_calm_mult=args.romantic_calm_mult,
        )
        style_model, style_rep = train_head(
            "style",
            X_train,
            y_style_train,
            X_val,
            y_style_val,
            epochs=args.epochs,
            batch_size=args.batch_size,
            pos_weight=pw,
            weighted_sampler=sampler,
        )
        torch.save(style_model.state_dict(), mlp_dir / "mlp_style_best.pth")
        torch.save(style_model.state_dict(), MODELS_DIR / "mlp_style_best.pth")
        report["style"] = {
            **style_rep,
            "pos_weight": pw.tolist(),
            "cozy_mult": args.cozy_mult,
            "romantic_calm_mult": args.romantic_calm_mult,
        }
    else:
        print(
            "Style head skipped (default). After v3 distribution looks good, run with --train-style."
        )

    report_path = Path(args.dataset).parent / "training_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved place/mood MLP to {mlp_dir} and {MODELS_DIR}")


if __name__ == "__main__":
    main()
