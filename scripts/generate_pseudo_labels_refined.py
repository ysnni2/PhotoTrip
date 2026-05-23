"""
Refined pseudo-label generator (Kaggle-ready).

Default v3 outputs:
  pseudo_labels_refined_v3.json
  label_distribution_report_v3.json
  pseudo_labels_balanced_v3.json (optional downsampled training subset)
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

from PIL import Image

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from analyzers.pseudo_evidence import extract_visual_evidence  # noqa: E402
from analyzers.labels import MOOD_LABELS, PLACE_LABELS, STYLE_LABELS  # noqa: E402

KAGGLE_WORKING = Path("/kaggle/working")
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

RARE_STYLES = frozenset({"cozy", "romantic", "calm"})
OVER_STYLES = frozenset({"energetic", "local", "aesthetic"})
DEFAULT_OVER_CAPS = {
    "energetic": 450,
    "local": 550,
    "aesthetic": 480,
}


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


def _style_multihot_dict(record: Mapping[str, Any]) -> Dict[str, float]:
    if isinstance(record.get("style_multihot"), dict):
        return dict(record["style_multihot"])
    y = record.get("y_style")
    if isinstance(y, list) and len(y) == len(STYLE_LABELS):
        return {lab: float(y[i]) for i, lab in enumerate(STYLE_LABELS)}
    return {s: 0.0 for s in STYLE_LABELS}


def _active_styles(multihot: Mapping[str, float]) -> Set[str]:
    return {s for s in STYLE_LABELS if float(multihot.get(s, 0.0)) >= 0.5}


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
        "style_multihot": ev.get("style_multihot"),
        "label_status": ev.get("label_status"),
        "discard_reason": ev.get("discard_reason"),
        "rule_hits": ev.get("rule_hits"),
        "primary_rule_hits": ev.get("primary_rule_hits"),
        "supplement_rule_hits": ev.get("supplement_rule_hits"),
        "y_place": y_place,
        "y_mood": y_mood,
        "y_style": y_style,
        "style_target_order": list(STYLE_LABELS),
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
            key=lambda x: (
                0 if x.get("label_status") == "hard" else 1,
                -float(x.get("category_confidence", 0)),
            ),
        )
        out.extend(items[:n])
    return out


def downsample_overrepresented(
    records: Sequence[Mapping[str, Any]],
    *,
    caps: Mapping[str, int],
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    MLP training subset: keep all multihot rare (cozy/romantic/calm) samples;
    lightly cap images whose multihot is only energetic/local/aesthetic.
    """
    rng = random.Random(seed)
    usable = [
        dict(r)
        for r in records
        if r.get("label_status") in ("hard", "weak")
        and _active_styles(_style_multihot_dict(r))
    ]
    rare_keep: List[Dict[str, Any]] = []
    over_buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    other: List[Dict[str, Any]] = []

    for r in usable:
        active = _active_styles(_style_multihot_dict(r))
        if active & RARE_STYLES:
            rare_keep.append(r)
            continue
        if active and active <= OVER_STYLES:
            dominant = max(active, key=lambda s: _style_multihot_dict(r).get(s, 0.0))
            over_buckets[dominant].append(r)
        else:
            other.append(r)

    kept_ids = {id(r) for r in rare_keep}
    out = list(rare_keep)

    for style, bucket in over_buckets.items():
        cap = int(caps.get(style, len(bucket)))
        ranked = sorted(
            bucket,
            key=lambda x: (
                0 if x.get("label_status") == "hard" else 1,
                -float(x.get("category_confidence", 0)),
            ),
        )
        for r in ranked[:cap]:
            if id(r) not in kept_ids:
                out.append(r)
                kept_ids.add(id(r))

    for r in other:
        if id(r) not in kept_ids:
            out.append(r)
            kept_ids.add(id(r))

    rng.shuffle(out)
    return out


def _supplement_rule_counts(records: Sequence[Mapping[str, Any]], style: str) -> Counter:
    counts: Counter = Counter()
    for r in records:
        for hit in r.get("supplement_rule_hits") or []:
            if isinstance(hit, dict) and hit.get("style") == style:
                counts[str(hit.get("rule", "unknown"))] += 1
        for hit in r.get("rule_hits") or []:
            if (
                isinstance(hit, dict)
                and hit.get("style") == style
                and hit.get("tier") == "supplement"
            ):
                counts[str(hit.get("rule", "unknown"))] += 1
    return counts


def report(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    primary = Counter(str(r.get("refined_style_label") or "none") for r in records)
    multihot_counts = Counter()
    for r in records:
        for s in _active_styles(_style_multihot_dict(r)):
            multihot_counts[s] += 1
    status = Counter(str(r.get("label_status")) for r in records)
    cozy_mh = int(multihot_counts.get("cozy", 0))
    romantic_mh = int(multihot_counts.get("romantic", 0))
    calm_mh = int(multihot_counts.get("calm", 0))
    return {
        "total": len(records),
        "label_status": dict(status),
        "primary_style_counts": dict(primary),
        "style_multihot_counts": dict(multihot_counts),
        "multihot_targets": {
            "cozy": {"count": cozy_mh, "min": 100, "met": cozy_mh >= 100},
            "romantic": {"count": romantic_mh, "min": 80, "met": romantic_mh >= 80},
            "calm": {"count": calm_mh, "min": 100, "met": calm_mh >= 100},
        },
        "cozy_supplement_rule_counts": dict(_supplement_rule_counts(records, "cozy")),
        "romantic_supplement_rule_counts": dict(_supplement_rule_counts(records, "romantic")),
        "category_counts": dict(Counter(str(r.get("category")) for r in records)),
        "mlp_training_note": (
            "Train MLP on style_multihot (y_style) from training_subset; "
            "primary_style_counts is audit-only."
        ),
    }


def run(
    *,
    input_json: Optional[Path],
    train_dir: Optional[Path],
    output_dir: Path,
    limit: Optional[int],
    use_segment: bool,
    use_gemini: bool,
    version: str = "v3",
    downsample: bool = True,
    seed: int = 42,
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
    training_subset = (
        downsample_overrepresented(refined, caps=DEFAULT_OVER_CAPS, seed=seed)
        if downsample
        else [r for r in refined if r.get("label_status") in ("hard", "weak")]
    )

    rep = {
        "version": version,
        "skipped": skipped,
        "refined_full": report(refined),
        "training_subset_mlp": report(training_subset),
        "balanced_primary_audit_only": report(balanced),
        "use_segment": use_segment,
        "use_gemini": use_gemini,
        "downsample_caps": DEFAULT_OVER_CAPS if downsample else None,
        "style_target_order": list(STYLE_LABELS),
        "default_mlp_input": "pseudo_labels_training_v3.json",
    }

    suffix = f"_{version}" if version else ""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "refined": output_dir / f"pseudo_labels_refined{suffix}.json",
        "balanced": output_dir / f"pseudo_labels_balanced{suffix}.json",
        "training": output_dir / f"pseudo_labels_training{suffix}.json",
        "report": output_dir / f"label_distribution_report{suffix}.json",
    }
    paths["refined"].write_text(json.dumps(refined, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["balanced"].write_text(json.dumps(balanced, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["training"].write_text(
        json.dumps(training_subset, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    paths["report"].write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    return paths


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=str, default=None, help="pseudo_labels.json")
    p.add_argument("--train-dir", type=str, default=str(_ROOT / "data" / "train"))
    p.add_argument(
        "--output-dir",
        type=str,
        default=str(
            KAGGLE_WORKING if KAGGLE_WORKING.is_dir() else _ROOT / "outputs" / "pseudo_labels"
        ),
    )
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--segment", action="store_true")
    p.add_argument("--no-gemini", action="store_true")
    p.add_argument("--version", type=str, default="v3")
    p.add_argument("--no-downsample", action="store_true")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    paths = run(
        input_json=Path(args.input) if args.input else None,
        train_dir=Path(args.train_dir) if args.train_dir else None,
        output_dir=Path(args.output_dir),
        limit=args.limit,
        use_segment=args.segment,
        use_gemini=not args.no_gemini,
        version=args.version,
        downsample=not args.no_downsample,
        seed=args.seed,
    )
    for k, v in paths.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
