"""
Combined lifestyle vectors (place / mood / interest) and CSV export.

Execution (project root = ``cv_project/``):

  Recommended — module mode (add ``backend`` to PYTHONPATH)::

      # Windows PowerShell
      $env:PYTHONPATH = "backend"
      python -m analyzers.lifestyle_analyzer test_images/sample.jpg

      # Linux / macOS
      PYTHONPATH=backend python -m analyzers.lifestyle_analyzer test_images/sample.jpg

  From ``backend/`` directory::

      python -m analyzers.lifestyle_analyzer ../test_images/sample.jpg

  Direct script (import fallback)::

      python backend/analyzers/lifestyle_analyzer.py test_images/sample.jpg

CSV default: ``outputs/lifestyle_vectors.csv`` (project root).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Union

from PIL import Image

_BACKEND_DIR = Path(__file__).resolve().parent.parent


def _ensure_backend_on_path() -> None:
    if str(_BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(_BACKEND_DIR))


try:
    from ._paths import DEFAULT_LIFESTYLE_CSV
    from .interest_analyzer import INTEREST_LABELS, analyze_interest
    from .mood_analyzer import MOOD_LABELS, analyze_mood
    from .place_analyzer import PLACE_LABELS, analyze_place
except ImportError:
    _ensure_backend_on_path()
    from analyzers._paths import DEFAULT_LIFESTYLE_CSV
    from analyzers.interest_analyzer import INTEREST_LABELS, analyze_interest
    from analyzers.mood_analyzer import MOOD_LABELS, analyze_mood
    from analyzers.place_analyzer import PLACE_LABELS, analyze_place

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
_DEFAULT_CSV = DEFAULT_LIFESTYLE_CSV


def analyze_lifestyle(image: Image.Image) -> Dict[str, Dict[str, float]]:
    """
    CLIP zero-shot lifestyle vectors for one image.

    Returns:
        {
            "place_vector": {beach: p, ...},
            "mood_vector": {calm: p, ...},
            "interest_vector": {sports: p, ...},
        }
    """
    return {
        "place_vector": analyze_place(image),
        "mood_vector": analyze_mood(image),
        "interest_vector": analyze_interest(image),
    }


def collect_image_paths(input_path: Union[str, Path]) -> List[Path]:
    """Resolve a single image file or all images under a directory."""
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input not found: {path}")

    if path.is_file():
        if path.suffix.lower() not in _IMAGE_SUFFIXES:
            raise ValueError(f"Not an image file: {path}")
        return [path]

    paths = sorted(
        p
        for p in path.rglob("*")
        if p.is_file() and p.suffix.lower() in _IMAGE_SUFFIXES
    )
    if not paths:
        raise FileNotFoundError(f"No images under {path}")
    return paths


def analyze_lifestyle_path(
    input_path: Union[str, Path],
) -> List[Dict[str, Any]]:
    """Run lifestyle analysis on one image or every image in a folder."""
    rows: List[Dict[str, Any]] = []
    for img_path in collect_image_paths(input_path):
        image = Image.open(img_path).convert("RGB")
        vectors = analyze_lifestyle(image)
        rows.append({"image_path": str(img_path.resolve()), **vectors})
    return rows


def lifestyle_rows_to_flat(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Flatten nested vectors for CSV export."""
    flat: Dict[str, Any] = {"image_path": row["image_path"]}
    for vec_name, labels in (
        ("place_vector", PLACE_LABELS),
        ("mood_vector", MOOD_LABELS),
        ("interest_vector", INTEREST_LABELS),
    ):
        vec = row.get(vec_name, {})
        for label in labels:
            flat[f"{vec_name}.{label}"] = float(vec.get(label, 0.0))
    return flat


def save_lifestyle_csv(
    rows: Sequence[Mapping[str, Any]],
    output_path: Union[str, Path] = _DEFAULT_CSV,
) -> Path:
    """Write lifestyle analysis rows to CSV."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    flat_rows = [lifestyle_rows_to_flat(r) for r in rows]
    fieldnames = list(flat_rows[0].keys()) if flat_rows else ["image_path"]

    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flat_rows)

    return out


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="CLIP lifestyle vectors (place / mood / interest) → CSV",
    )
    p.add_argument(
        "input",
        type=str,
        help="Path to a single image or a folder of images",
    )
    p.add_argument(
        "--output",
        type=str,
        default=str(_DEFAULT_CSV),
        help=f"CSV output path (default: {_DEFAULT_CSV})",
    )
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    rows = analyze_lifestyle_path(args.input)
    out = save_lifestyle_csv(rows, args.output)
    print(f"Analyzed {len(rows)} image(s) → {out}")


if __name__ == "__main__":
    # Direct: python backend/analyzers/lifestyle_analyzer.py <input>
    if __package__ is None:
        _ensure_backend_on_path()
        from analyzers.lifestyle_analyzer import main as _main

        _main()
    else:
        main()
