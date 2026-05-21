"""
Smoke test for enhanced analyzers (culture subtype, interest tags, festival hybrid).

Usage (single image)::

    python scripts/test_enhanced_analyzer.py --image path/to/image.jpg

Three-scenario demo (culture / food / festival from data/train)::

    python scripts/test_enhanced_analyzer.py --demo

Explicit triple with validation hints::

    python scripts/test_enhanced_analyzer.py \\
      --image culture.jpg --scenario culture \\
      --image food.jpg --scenario food \\
      --image festival.jpg --scenario festival
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from PIL import Image

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from analyzers.pseudo_evidence import extract_visual_evidence  # noqa: E402

SCENARIOS = ("culture", "food", "festival")


def build_output_schema(record: Mapping[str, Any]) -> Dict[str, Any]:
    """Final JSON schema for console inspection."""
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
        # helpful extras (not required but useful when debugging)
        "category_confidence": record.get("category_confidence"),
        "culture_confidence": record.get("culture_confidence"),
        "festival_subtype": record.get("festival_subtype"),
        "festival_confidence": record.get("festival_confidence"),
        "gemini_fallback_used": record.get("gemini_fallback_used", False),
        "primary_style": record.get("primary_style"),
    }


def _load_segment(image: Image.Image, enabled: bool) -> Optional[Dict[str, float]]:
    if not enabled:
        return None
    try:
        from oneformer import segment

        return segment(image)
    except Exception:
        return None


def analyze_image(
    image_path: Path,
    *,
    use_segment: bool,
    use_gemini: bool,
) -> Dict[str, Any]:
    image = Image.open(image_path).convert("RGB")
    segment_result = _load_segment(image, use_segment)
    record = extract_visual_evidence(
        image,
        segment_result=segment_result,
        use_siglip_category=False,
        use_gemini_festival=use_gemini,
    )
    return build_output_schema(record)


def check_scenario(scenario: str, out: Mapping[str, Any]) -> List[str]:
    """Return human-readable pass/warn notes for the three demo cases."""
    notes: List[str] = []
    tags = {str(t.get("tag", "")) for t in out.get("interest_tags") or []}

    if scenario == "culture":
        if out.get("category") != "culture":
            notes.append(f"WARN: category={out.get('category')} (expected culture)")
        else:
            notes.append("OK: category is culture")
        if out.get("top_culture_subtype"):
            notes.append(f"OK: top_culture_subtype={out.get('top_culture_subtype')}")
        else:
            notes.append("WARN: top_culture_subtype is null (Gemini fallback may be needed)")
        if out.get("culture_subtype_scores"):
            notes.append("OK: culture_subtype_scores present")

    elif scenario == "food":
        if out.get("category") == "food":
            notes.append("OK: category is food")
        elif "cafe" in tags:
            notes.append(f"OK: interest tag cafe present (category={out.get('category')})")
        else:
            notes.append(f"WARN: expected food category or cafe tag (category={out.get('category')}, tags={tags})")
        if tags & {"cafe", "local_market"}:
            notes.append(f"OK: food-related interest tags: {sorted(tags & {'cafe', 'local_market'})}")
        else:
            notes.append(f"WARN: no cafe/local_market tags (tags={sorted(tags)})")

    elif scenario == "festival":
        fest = out.get("festival_evidence") or {}
        if out.get("category") == "festival":
            notes.append("OK: category is festival")
        else:
            notes.append(f"NOTE: category={out.get('category')} (festival evidence still reported)")
        if fest:
            notes.append(f"OK: festival_evidence={fest}")
        else:
            notes.append("WARN: festival_evidence empty")
        if out.get("gemini_fallback_needed"):
            notes.append("OK: gemini_fallback_needed=true (ambiguous festival scene)")
        if out.get("gemini_fallback_used"):
            notes.append(f"OK: Gemini used → festival_subtype={out.get('festival_subtype')}")
        elif out.get("festival_subtype"):
            notes.append(f"OK: festival_subtype={out.get('festival_subtype')} (CV/heuristic)")

    return notes


def default_demo_cases() -> List[Tuple[str, Path]]:
    """Pick one pseudo image per category from data/train if available."""
    train = _ROOT / "data" / "train"
    cases: List[Tuple[str, Path]] = []
    mapping = (
        ("culture", "culture"),
        ("food", "food"),
        ("festival", "festival"),
    )
    for folder, scenario in mapping:
        cat_dir = train / folder
        if not cat_dir.is_dir():
            continue
        imgs = sorted(cat_dir.glob("pseudo_*.jpg"))
        if imgs:
            cases.append((scenario, imgs[0]))
    return cases


def run_case(
    image_path: Path,
    *,
    scenario: Optional[str],
    use_segment: bool,
    use_gemini: bool,
) -> None:
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    print("=" * 72)
    if scenario:
        print(f"Scenario: {scenario}")
    print(f"Image: {image_path.resolve()}\n")

    out = analyze_image(image_path, use_segment=use_segment, use_gemini=use_gemini)
    print(json.dumps(out, ensure_ascii=False, indent=2))

    if scenario:
        print("\nChecks:")
        for line in check_scenario(scenario, out):
            print(f"  - {line}")
    print()


def parse_cases(args: argparse.Namespace) -> List[Tuple[Optional[str], Path]]:
    if args.demo:
        demo = default_demo_cases()
        if len(demo) < 3:
            found = [s for s, _ in demo]
            missing = [s for s in SCENARIOS if s not in found]
            print(
                f"WARNING: --demo found only {len(demo)}/3 cases. Missing folders: {missing}",
                file=sys.stderr,
            )
        return demo

    images: List[str] = args.image or []
    if not images:
        return []

    scenarios: List[Optional[str]] = list(args.scenario or [])
    while len(scenarios) < len(images):
        scenarios.append(None)

    return [(scenarios[i], Path(images[i])) for i in range(len(images))]


def main() -> None:
    p = argparse.ArgumentParser(description="Test enhanced analyzer output schema")
    p.add_argument(
        "--image",
        action="append",
        default=[],
        help="Image path (repeat for multiple; use with --scenario)",
    )
    p.add_argument(
        "--scenario",
        action="append",
        choices=SCENARIOS,
        help="Optional: culture | food | festival (same order as --image)",
    )
    p.add_argument(
        "--demo",
        action="store_true",
        help="Run 3 checks using one image each from data/train/{culture,food,festival}",
    )
    p.add_argument("--segment", action="store_true", help="Enable OneFormer segmentation")
    p.add_argument("--no-gemini", action="store_true", help="Disable Gemini festival fallback")
    args = p.parse_args()

    cases = parse_cases(args)
    if not cases:
        p.error("Provide --image PATH or use --demo")

    use_segment = args.segment
    use_gemini = not args.no_gemini

    print("Enhanced analyzer test")
    print(f"  segment={use_segment}, gemini_festival={use_gemini}\n")

    for scenario, path in cases:
        run_case(path, scenario=scenario, use_segment=use_segment, use_gemini=use_gemini)


if __name__ == "__main__":
    main()
