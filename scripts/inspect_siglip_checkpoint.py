"""Inspect models/best_siglip.pth layout (training dict vs flat state_dict)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "backend"))

from siglip_classifier import inspect_checkpoint  # noqa: E402

if __name__ == "__main__":
    inspect_checkpoint(_ROOT / "models" / "best_siglip.pth")
