"""
Refined pseudo-label generator (Kaggle-ready).

Input: pseudo_labels.json OR data/train scan
Output: pseudo_labels_refined.json, pseudo_labels_balanced.json, label_distribution_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from PIL import Image

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from analyzers.pseudo_evidence import extract_visual_evidence  # noqa: E402
from analyzers.labels import MOOD_LABELS, PLACE_LABELS, STYLE_LABELS  # noqa: E402

KAGGLE_WORKING = Path("/kaggle/working")
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def load_manifest(path: Path) -> List[Dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    for key in ("labels", "records", "data"):
        if isinstance(raw.get(key), list):
            return list(raw[key])
    raise ValueError(f"Unsupported JSON: {path}")


def collect_from_train(train_dir: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for cat_dir in sorted(train_dir.iterdir()):
        if not cat_dir.is_dir():
            continue
        for img in sorted(cat_dir.glob("pseudo_*.*")):
            if img.suffix.lower() in _IMAGE_SUFFIXES:
                rows.append(
                    {"image_path": str(img.resolve()), "folder_category": cat_dir.name.lower()}
                )
    return rows


def resolve_path(entry: Mapping[str, Any], train_dir: Optional[Path]) -> Optional[Path]:
    for key in ("image_path", "path", "file"):
        raw = entry.get(key)
        if not raw:
            continue
        p = Path(str(raw))
        if p.is_file():
            return p
        if train_dir and (train_dir / p.name).is_file():
            return train_dir / p.name
        folder = str(entry.get("folder_category", entry.get("category", ""))).lower()
        if folder and train_dir:
            cand = train_dir / folder / p.name
            if cand.is_file():
                return cand
    return None


def process_image(
    image_path: Path,
    entry: Mapping[str, Any],
    *,
    use_segment: bool,
    use_gemini: bool,
) -> Dict[str, Any]:
    image = Image.open(image_path).convert("RGB")
    segment_result = None
    if use_segment:
        try:
            from oneformer import segment

            segment_result = segment(image)
        except Exception:
            pass

    ev = extract_visual_evidence(
        image, segment_result=segment_result, use_gemini_festival=use_gemini
    )

    y_place = [ev["place_multihot"].get(l, 0.0) for l in PLACE_LABELS]
    y_mood = [ev["mood_multihot"].get(l, 0.0) for l in MOOD_LABELS]
    y_style = [ev.get("style_multihot", {}).get(l, 0.0) for l in STYLE_LABELS]

    return {
        "image_path": str(image_path),
        "folder_category": entry.get("folder_category", ""),
        "category": ev["category"],
        "category_confidence": ev.get("category_confidence"),
        "category_scores": ev.get("category_scores"),
        "top_culture_subtype": ev.get("top_culture_subtype"),
        "culture_subtype_scores": ev.get("culture_subtype_scores"),
        "culture_confidence": ev.get("culture_confidence"),
        "interest_tags": ev.get("interest_tags"),
        "visual_tone": ev.get("visual_tone"),
        "festival_evidence": ev.get("festival_evidence"),
        "festival_subtype": ev.get("festival_subtype"),
        "refined_style_label": ev.get("refined_style_label"),
        "style_candidates": ev.get("style_candidates"),
        "label_status": ev.get("label_status"),
        "discard_reason": ev.get("discard_reason"),
        "rule_hits": ev.get("rule_hits"),
        "y_place": y_place,
        "y_mood": y_mood,
        "y_style": y_style,
        "gemini_fallback_needed": ev.get("gemini_fallback_needed", False),
    }


def balanced_subset(records: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    usable = [
        dict(r)
        for r in records
        if r.get("label_status") in ("hard", "weak") and r.get("refined_style_label")
    ]
    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in usable:
        buckets[str(r["refined_style_label"])].append(r)
    if not buckets:
        return []
    n = min(len(v) for v in buckets.values())
    out: List[Dict[str, Any]] = []
    for k in sorted(buckets):
        items = sorted(
            buckets[k],
            key=lambda x: (0 if x.get("label_status") == "hard" else 1, -float(x.get("category_confidence", 0))),
        )
        out.extend(items[:n])
    return out


def report(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        "total": len(records),
        "label_status": dict(Counter(str(r.get("label_status")) for r in records)),
        "style_counts": dict(Counter(str(r.get("refined_style_label") or "none") for r in records)),
        "category_counts": dict(Counter(str(r.get("category")) for r in records)),
    }


def run(
    *,
    input_json: Optional[Path],
    train_dir: Optional[Path],
    output_dir: Path,
    limit: Optional[int],
    use_segment: bool,
    use_gemini: bool,
) -> Dict[str, Path]:
    if input_json and input_json.is_file():
        entries = load_manifest(input_json)
    elif train_dir and train_dir.is_dir():
        entries = collect_from_train(train_dir)
    else:
        raise FileNotFoundError("Provide --input pseudo_labels.json or --train-dir")

    if limit:
        entries = entries[:limit]

    refined: List[Dict[str, Any]] = []
    skipped = 0
    for i, entry in enumerate(entries):
        path = resolve_path(entry, train_dir)
        if path is None:
            skipped += 1
            continue
        print(f"[{i+1}/{len(entries)}] {path.name}")
        refined.append(process_image(path, entry, use_segment=use_segment, use_gemini=use_gemini))

    balanced = balanced_subset(refined)
    rep = {
        "skipped": skipped,
        "refined": report(refined),
        "balanced": report(balanced),
        "use_segment": use_segment,
        "use_gemini": use_gemini,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "refined": output_dir / "pseudo_labels_refined.json",
        "balanced": output_dir / "pseudo_labels_balanced.json",
        "report": output_dir / "label_distribution_report.json",
    }
    paths["refined"].write_text(json.dumps(refined, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["balanced"].write_text(json.dumps(balanced, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["report"].write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    return paths


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=str, default=None, help="pseudo_labels.json")
    p.add_argument("--train-dir", type=str, default=str(_ROOT / "data" / "train"))
    p.add_argument(
        "--output-dir",
        type=str,
        default=str(KAGGLE_WORKING if KAGGLE_WORKING.is_dir() else _ROOT / "outputs" / "pseudo_labels"),
    )
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--segment", action="store_true")
    p.add_argument("--no-gemini", action="store_true")
    args = p.parse_args()

    paths = run(
        input_json=Path(args.input) if args.input else None,
        train_dir=Path(args.train_dir) if args.train_dir else None,
        output_dir=Path(args.output_dir),
        limit=args.limit,
        use_segment=args.segment,
        use_gemini=not args.no_gemini,
    )
    for k, v in paths.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
