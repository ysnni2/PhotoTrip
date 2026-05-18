"""Collect travel photos from Pixabay and pseudo-label with fine-tuned SigLIP."""

from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from PIL import Image
from tqdm import tqdm

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_ENV_PATH = _PROJECT_ROOT / ".env"

load_dotenv(_ENV_PATH)

if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from siglip_classifier import CLASS_NAMES, classify  # noqa: E402

PIXABAY_API_URL = "https://pixabay.com/api/"

SEARCH_QUERIES: Dict[str, str] = {
    "beach": "beach travel summer sea",
    "nature": "mountain hiking nature forest",
    "city": "city night skyline urban street",
    "culture": "museum temple culture historic",
    "festival": "concert festival music show",
    "food": "street food restaurant cafe meal",
}

DEFAULT_OUTPUT_DIR = Path("/content/data/train")
CONFIDENCE_THRESHOLD = 0.5
IMAGES_PER_CATEGORY = 100


def _pixabay_api_key() -> str:
    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key:
        raise EnvironmentError("PIXABAY_API_KEY environment variable is not set")
    return key


def fetch_pixabay_hits(
    api_key: str,
    query: str,
    *,
    per_page: int = IMAGES_PER_CATEGORY,
    page: int = 1,
) -> List[dict]:
    params = {
        "key": api_key,
        "q": query,
        "image_type": "photo",
        "orientation": "horizontal",
        "per_page": min(200, per_page),
        "page": page,
        "safesearch": "true",
    }
    resp = requests.get(PIXABAY_API_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return list(data.get("hits", []))


def download_image(url: str) -> Optional[Image.Image]:
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGB")
    except (requests.RequestException, OSError):
        return None


def _image_url(hit: dict) -> str:
    return str(
        hit.get("largeImageURL")
        or hit.get("webformatURL")
        or hit.get("previewURL")
        or ""
    )


def _top_prediction(scores: Dict[str, float]) -> Tuple[str, float]:
    if not scores:
        return "", 0.0
    label = max(scores, key=scores.get)
    return label, float(scores[label])


def _next_pseudo_index(out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    indices: List[int] = []
    for path in out_dir.glob("pseudo_*.jpg"):
        stem = path.stem
        if stem.startswith("pseudo_"):
            try:
                indices.append(int(stem.split("_", 1)[1]))
            except ValueError:
                continue
    return max(indices, default=-1) + 1


def collect_and_label_category(
    category: str,
    query: str,
    output_root: Path,
    api_key: str,
    *,
    target_count: int = IMAGES_PER_CATEGORY,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
) -> int:
    hits = fetch_pixabay_hits(api_key, query, per_page=target_count)
    out_dir = output_root / category
    saved = 0
    next_idx = _next_pseudo_index(out_dir)

    for hit in tqdm(hits, desc=category, leave=False):
        if saved >= target_count:
            break

        image = download_image(_image_url(hit))
        if image is None:
            continue

        scores = classify(image)
        pred_label, confidence = _top_prediction(scores)
        if pred_label != category or confidence < confidence_threshold:
            continue

        dest = out_dir / f"pseudo_{next_idx}.jpg"
        image.save(dest, format="JPEG", quality=92)
        next_idx += 1
        saved += 1

    return saved


def run(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    per_category: int = IMAGES_PER_CATEGORY,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
) -> Dict[str, int]:
    load_dotenv(_ENV_PATH, override=True)
    api_key = _pixabay_api_key()
    output_dir.mkdir(parents=True, exist_ok=True)

    from siglip_classifier import DEFAULT_MODEL_PATH

    print(f"Project root: {_PROJECT_ROOT}")
    print(f".env loaded: {_ENV_PATH.is_file()} ({_ENV_PATH})")
    print(f"SigLIP checkpoint: {DEFAULT_MODEL_PATH} (exists={DEFAULT_MODEL_PATH.is_file()})")
    print(f"Output: {output_dir.resolve()}")
    print("Loading SigLIP (first run may download ~1GB from Hugging Face, wait a few minutes)...")

    # Warm up SigLIP checkpoint once
    classify(Image.new("RGB", (64, 64), color=(128, 128, 128)))
    print("SigLIP ready. Fetching from Pixabay and labeling...\n")

    counts: Dict[str, int] = {}
    for category in CLASS_NAMES:
        query = SEARCH_QUERIES.get(category, category)
        counts[category] = collect_and_label_category(
            category,
            query,
            output_dir,
            api_key,
            target_count=per_category,
            confidence_threshold=confidence_threshold,
        )

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pixabay download + SigLIP pseudo-labeling for train folders.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help="Root train directory (default: /content/data/train)",
    )
    parser.add_argument(
        "--per_category",
        type=int,
        default=IMAGES_PER_CATEGORY,
        help="Pixabay images to fetch per category (default: 100)",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=CONFIDENCE_THRESHOLD,
        help="Minimum top-class confidence to keep (default: 0.5)",
    )
    args = parser.parse_args()

    counts = run(
        Path(args.output_dir),
        per_category=args.per_category,
        confidence_threshold=args.confidence,
    )

    print("\n=== Pseudo-labeling results ===")
    total = 0
    for category in CLASS_NAMES:
        n = counts.get(category, 0)
        total += n
        print(f"  {category}: +{n} images")
    print(f"  total: {total} images")
    print(f"  saved under: {args.output_dir}")


if __name__ == "__main__":
    main()
