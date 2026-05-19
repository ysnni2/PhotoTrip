"""Project paths for lifestyle CSV output."""

from __future__ import annotations

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_LIFESTYLE_CSV = PROJECT_ROOT / "outputs" / "lifestyle_vectors.csv"
