"""
Evaluate CLIP-only vs MLP-only vs ensemble multi-label heads.

Usage:
  python scripts/evaluate_multilabel.py --dataset outputs/multilabel_dataset.pt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

import torch
from PIL import Image
from tqdm import tqdm

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from analyzers.labels import MOOD_LABELS, PLACE_LABELS  # noqa: E402
from analyzers.ensemble_scorer import ensemble_mood_scores, ensemble_place_scores  # noqa: E402
from analyzers.mood_analyzer import analyze_mood  # noqa: E402
from analyzers.place_analyzer import analyze_place  # noqa: E402
from analyzers.mlp_head import load_mlp_head, mlp_multilabel_probs, clip_pooler_features  # noqa: E402


def _vec(scores: Dict[str, float], labels: List[str], threshold: float = 0.5) -> torch.Tensor:
    return torch.tensor([1.0 if scores.get(l, 0) >= threshold else 0.0 for l in labels])


def _metrics(pred: torch.Tensor, true: torch.Tensor) -> Dict[str, float]:
    tp = (pred * true).sum()
    fp = (pred * (1 - true)).sum()
    fn = ((1 - pred) * true).sum()
    p = float(tp / (tp + fp + 1e-8))
    r = float(tp / (tp + fn + 1e-8))
    f1 = float(2 * p * r / (p + r + 1e-8))
    hamming = float((pred != true).float().mean())
    subset = float((pred == true).all(dim=1).float().mean())
    return {"precision": p, "recall": r, "f1": f1, "hamming": hamming, "subset_acc": subset}


def evaluate_split(
    meta: List[Dict],
    X: torch.Tensor,
    y_place: torch.Tensor,
    y_mood: torch.Tensor,
    *,
    mlp_weight: float = 0.55,
    threshold: float = 0.5,
) -> Dict[str, Dict[str, float]]:
    place_clip_p, place_mlp_p, place_ens_p = [], [], []
    mood_clip_p, mood_mlp_p, mood_ens_p = [], [], []

    place_head = load_mlp_head("mlp_place_best.pth", len(PLACE_LABELS))
    mood_head = load_mlp_head("mlp_mood_best.pth", len(MOOD_LABELS))

    for i, row in enumerate(tqdm(meta, desc="eval")):
        path = Path(row["image_path"])
        image = Image.open(path).convert("RGB")

        clip_place = analyze_place(image)
        clip_mood = analyze_mood(image)
        pooler = X[i] if X.numel() else clip_pooler_features(image)

        mlp_place = (
            mlp_multilabel_probs(place_head, pooler)
            if place_head is not None
            else torch.tensor([clip_place[l] for l in PLACE_LABELS])
        )
        mlp_mood = (
            mlp_multilabel_probs(mood_head, pooler)
            if mood_head is not None
            else torch.tensor([clip_mood[l] for l in MOOD_LABELS])
        )

        ens_place = ensemble_place_scores(image, mlp_weight=mlp_weight)
        ens_mood = ensemble_mood_scores(image, mlp_weight=mlp_weight)

        place_clip_p.append(_vec(clip_place, PLACE_LABELS, threshold))
        place_mlp_p.append(_vec({l: float(mlp_place[j]) for j, l in enumerate(PLACE_LABELS)}, PLACE_LABELS, threshold))
        place_ens_p.append(_vec(ens_place, PLACE_LABELS, threshold))

        mood_clip_p.append(_vec(clip_mood, MOOD_LABELS, threshold))
        mood_mlp_p.append(_vec({l: float(mlp_mood[j]) for j, l in enumerate(MOOD_LABELS)}, MOOD_LABELS, threshold))
        mood_ens_p.append(_vec(ens_mood, MOOD_LABELS, threshold))

    Pc = torch.stack(place_clip_p)
    Pm = torch.stack(place_mlp_p)
    Pe = torch.stack(place_ens_p)
    Mc = torch.stack(mood_clip_p)
    Mm = torch.stack(mood_mlp_p)
    Me = torch.stack(mood_ens_p)

    return {
        "place_clip": _metrics(Pc, y_place),
        "place_mlp": _metrics(Pm, y_place),
        "place_ensemble": _metrics(Pe, y_place),
        "mood_clip": _metrics(Mc, y_mood),
        "mood_mlp": _metrics(Mm, y_mood),
        "mood_ensemble": _metrics(Me, y_mood),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=str, default=str(_ROOT / "outputs" / "multilabel_dataset.pt"))
    p.add_argument("--mlp-weight", type=float, default=0.55)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--output", type=str, default=None)
    args = p.parse_args()

    data = torch.load(args.dataset, map_location="cpu", weights_only=False)
    val_metrics = evaluate_split(
        data["val"]["meta"],
        data["val"]["X"],
        data["val"]["y_place"],
        data["val"]["y_mood"],
        mlp_weight=args.mlp_weight,
        threshold=args.threshold,
    )

    out_path = Path(args.output or Path(args.dataset).parent / "evaluation_report.json")
    out_path.write_text(json.dumps(val_metrics, indent=2), encoding="utf-8")
    print(json.dumps(val_metrics, indent=2))
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
