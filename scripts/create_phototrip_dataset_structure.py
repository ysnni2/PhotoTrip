"""
Create PhotoTrip dataset directory layout (empty class folders).

Usage:
  python scripts/create_phototrip_dataset_structure.py
  python scripts/create_phototrip_dataset_structure.py --root ./my_data
"""

from __future__ import annotations

import argparse
from pathlib import Path

BASELINE_CLASSES = (
    "beach",
    "nature",
    "city",
    "indoor",
    "culture",
    "fashion",
    "food",
)

STYLE_PROBE_STYLES = (
    "luxury",
    "cozy",
    "vibrant",
    "minimal",
    "romantic",
    "adventurous",
)


def create_layout(root: Path) -> None:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)

    baseline = root / "baseline_train_v1"
    for name in BASELINE_CLASSES:
        (baseline / name).mkdir(parents=True, exist_ok=True)

    (root / "external_validation_v1").mkdir(parents=True, exist_ok=True)

    probe = root / "style_probe_v1"
    for name in STYLE_PROBE_STYLES:
        (probe / name).mkdir(parents=True, exist_ok=True)

    (root / "metadata").mkdir(parents=True, exist_ok=True)

    # Keep empty dirs in git-friendly way (optional)
    for marker_parent in (root / "external_validation_v1", root / "metadata"):
        marker = marker_parent / ".gitkeep"
        if not marker.exists():
            marker.write_text("", encoding="utf-8")

    print(f"Created PhotoTrip dataset layout under:\n  {root}\n")
    print("baseline_train_v1:", ", ".join(BASELINE_CLASSES))
    print("style_probe_v1:", ", ".join(STYLE_PROBE_STYLES))
    print("external_validation_v1/, metadata/ (with .gitkeep if empty)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create PhotoTrip dataset folder structure (baseline, validation, style probe, metadata).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("phototrip_dataset"),
        help="Root directory for the dataset tree (default: ./phototrip_dataset)",
    )
    args = parser.parse_args()
    create_layout(args.root)


if __name__ == "__main__":
    main()
