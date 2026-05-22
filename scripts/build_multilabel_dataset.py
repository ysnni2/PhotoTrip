"""
Build multi-label CLIP pooler dataset from pseudo_labels_refined_v3.json.

Outputs:
  multilabel_dataset_v3.pt — train/val + y_style [calm, cozy, romantic, energetic, local, aesthetic]
  dataset_report_v3.json — pos_weight (clamped max 10), style pos rates
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

import torch
from PIL import Image
from tqdm import tqdm

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from analyzers.labels import MOOD_LABELS, PLACE_LABELS, STYLE_LABELS  # noqa: E402
from analyzers.mlp_head import clip_pooler_features  # noqa: E402
from analyzers.multilabel_utils import (  # noqa: E402
    STYLE_TARGET_ORDER,
    compute_pos_weight,
    multilabel_style_pos_rates,
)

KAGGLE_WORKING = Path("/kaggle/working")


def load_refined(path: Path) -> List[Dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else list(raw["records"])


def vector_from_record(row: Dict[str, Any], labels: Sequence[str], key: str) -> List[float]:
    if key in row and isinstance(row[key], list):
        return [float(v) for v in row[key]]
    blob = row.get(key.replace("y_", "") + "_multihot", {})
    if isinstance(blob, dict):
        return [float(blob.get(l, 0.0)) for l in labels]
    return [0.0] * len(labels)


def build(
    refined_path: Path,
    output_path: Path,
    *,
    val_ratio: float = 0.15,
    seed: int = 42,
    only_usable: bool = True,
    precompute_pooler: bool = True,
    use_training_subset: bool = False,
) -> Dict[str, Any]:
    rows = load_refined(refined_path)
    if only_usable:
        rows = [r for r in rows if r.get("label_status") in ("hard", "weak")]

    random.seed(seed)
    random.shuffle(rows)
    n_val = max(1, int(len(rows) * val_ratio)) if rows else 0
    val_rows = rows[:n_val]
    train_rows = rows[n_val:]

    def pack(split_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        xs: List[torch.Tensor] = []
        yp: List[List[float]] = []
        ym: List[List[float]] = []
        ys: List[List[float]] = []
        meta: List[Dict[str, Any]] = []
        for row in tqdm(split_rows, desc="pooler"):
            path = Path(str(row["image_path"]))
            if precompute_pooler and path.is_file():
                pooler = clip_pooler_features(Image.open(path).convert("RGB"))
            else:
                pooler = torch.zeros(768)
            xs.append(pooler)
            yp.append(vector_from_record(row, PLACE_LABELS, "y_place"))
            ym.append(vector_from_record(row, MOOD_LABELS, "y_mood"))
            ys.append(vector_from_record(row, STYLE_LABELS, "y_style"))
            meta.append(
                {
                    "image_path": str(path),
                    "category": row.get("category"),
                    "refined_style_label": row.get("refined_style_label"),
                    "label_status": row.get("label_status"),
                    "style_multihot": row.get("style_multihot"),
                }
            )
        n_style = len(STYLE_TARGET_ORDER)
        if not xs:
            return {
                "X": torch.zeros(0, 768),
                "y_place": torch.zeros(0, len(PLACE_LABELS)),
                "y_mood": torch.zeros(0, len(MOOD_LABELS)),
                "y_style": torch.zeros(0, n_style),
                "meta": [],
            }
        return {
            "X": torch.stack(xs),
            "y_place": torch.tensor(yp, dtype=torch.float32),
            "y_mood": torch.tensor(ym, dtype=torch.float32),
            "y_style": torch.tensor(ys, dtype=torch.float32),
            "meta": meta,
        }

    train_pack = pack(train_rows)
    val_pack = pack(val_rows)
    pos_weight = compute_pos_weight(train_pack["y_style"])

    dataset = {
        "train": train_pack,
        "val": val_pack,
        "labels": {
            "place": PLACE_LABELS,
            "mood": MOOD_LABELS,
            "style": STYLE_TARGET_ORDER,
        },
        "style_pos_weight": pos_weight,
        "sampler_config": {
            "cozy_mult": 4.0,
            "romantic_calm_mult": 2.5,
            "description": "cozy 3-5x; romantic/calm 2-3x via rare_label_sample_weights",
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(dataset, output_path)

    report = {
        "train_size": int(dataset["train"]["X"].shape[0]),
        "val_size": int(dataset["val"]["X"].shape[0]),
        "style_target_order": STYLE_TARGET_ORDER,
        "style_pos_weight": pos_weight.tolist(),
        "style_pos_rate_train": multilabel_style_pos_rates(train_pack["y_style"]),
        "style_pos_rate_val": multilabel_style_pos_rates(val_pack["y_style"]),
        "place_pos_rate": dataset["train"]["y_place"].mean(dim=0).tolist()
        if dataset["train"]["X"].numel()
        else [],
        "mood_pos_rate": dataset["train"]["y_mood"].mean(dim=0).tolist()
        if dataset["train"]["X"].numel()
        else [],
        "source": str(refined_path),
        "use_training_subset": use_training_subset,
    }
    if "v3" in output_path.stem:
        report_path = output_path.parent / "dataset_report_v3.json"
    else:
        report_path = output_path.parent / "dataset_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"dataset": output_path, "report": report_path, "stats": report}


def main() -> None:
    p = argparse.ArgumentParser()
    default_in = KAGGLE_WORKING / "pseudo_labels_refined_v3.json"
    if not default_in.is_file():
        default_in = _ROOT / "outputs" / "pseudo_labels" / "pseudo_labels_refined_v3.json"
    if not default_in.is_file():
        default_in = _ROOT / "outputs" / "pseudo_labels" / "pseudo_labels_training_v3.json"
    p.add_argument("--input", type=str, default=str(default_in))
    p.add_argument(
        "--output",
        type=str,
        default=str(
            KAGGLE_WORKING / "multilabel_dataset_v3.pt"
            if KAGGLE_WORKING.is_dir()
            else _ROOT / "outputs" / "multilabel_dataset_v3.pt"
        ),
    )
    p.add_argument("--val-ratio", type=float, default=0.15)
    p.add_argument(
        "--training-subset",
        action="store_true",
        help="Use pseudo_labels_training_v3.json if present",
    )
    args = p.parse_args()

    input_path = Path(args.input)
    if args.training_subset:
        alt = input_path.parent / "pseudo_labels_training_v3.json"
        if alt.is_file():
            input_path = alt

    out = build(input_path, Path(args.output), use_training_subset=args.training_subset)
    print(json.dumps(out["stats"], indent=2))
    print(f"saved: {out['dataset']}")


if __name__ == "__main__":
    main()
