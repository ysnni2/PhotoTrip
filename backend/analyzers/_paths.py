from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
MODELS_DIR = PROJECT_ROOT / "models"
DEFAULT_LIFESTYLE_CSV = PROJECT_ROOT / "outputs" / "lifestyle_vectors.csv"
DEFAULT_PSEUDO_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "pseudo_labels"
