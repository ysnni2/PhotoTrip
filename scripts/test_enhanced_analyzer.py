"""Test enhanced analyzer output schema on one or more images."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from analyzers.pseudo_evidence import extract_visual_evidence  # noqa: E402


def to_schema(record: dict) -> dict:
    return {
        "category": record.get("category"),
        "category_scores": record.get("category_scores", {}),
        "culture_subtype_scores": record.get("culture_subtype_scores", {}),
        "top_culture_subtype": record.get("top_culture_subtype"),
        "interest_tags": record.get("interest_tags", []),
        "visual_tone": record.get("visual_tone", {}),
        "festival_evidence": record.get("festival_evidence", {}),
        "style_candidates": record.get("style_candidates", []),
        "gemini_fallback_needed": record.get("gemini_fallback_needed", False),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--image", action="append", required=True)
    p.add_argument("--segment", action="store_true")
    p.add_argument("--no-gemini", action="store_true")
    args = p.parse_args()

    for img_path in args.image:
        path = Path(img_path)
        image = Image.open(path).convert("RGB")
        seg = None
        if args.segment:
            from oneformer import segment, segment_ratios

            seg = segment_ratios(segment(image))
        record = extract_visual_evidence(
            image, segment_result=seg, use_gemini_festival=not args.no_gemini
        )
        print(f"Image: {path}\n")
        print(json.dumps(to_schema(record), ensure_ascii=False, indent=2))
        print()


if __name__ == "__main__":
    main()
