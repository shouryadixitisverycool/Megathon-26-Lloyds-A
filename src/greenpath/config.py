"""Central run configuration: seeds, timeline and artifact locations (spec 5, 56)."""

from datetime import date, datetime, time
import os
from pathlib import Path

SEED_DATA = 42
SEED_SPLIT = 43
SEED_MODEL = 44
SEED_PERTURBATION = 45

FEATURE_CUTOFF = date(2026, 6, 30)
OUTCOME_WINDOW_DAYS = 90
OUTCOME_WINDOW_END = date(2026, 9, 28)
PREDICTION_TIMESTAMP = datetime.combine(date(2026, 10, 10), time(9, 0))
# Earlier cutoff for the optional temporal holdout (spec 9.3) and monthly trend scoring.
TEMPORAL_HOLDOUT_CUTOFF = date(2026, 3, 31)
TREND_CUTOFFS = [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31),
                 date(2026, 4, 30), date(2026, 5, 31), date(2026, 6, 30)]

# Simulated history covers the feature window, earlier context and the outcome window.
HISTORY_START = date(2025, 1, 1)
HISTORY_END = OUTCOME_WINDOW_END

FEATURE_VERSION = "feature_v1"

# Source checkouts write beside pyproject.toml; installed wheels use the caller's
# workspace instead of writing into site-packages. The override supports both.
_source_root = Path(__file__).resolve().parents[3]
REPO_ROOT = Path(os.environ.get(
    "GREENPATH_WORKSPACE",
    str(_source_root if (_source_root / "pyproject.toml").is_file() else Path.cwd()),
)).expanduser().resolve()
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "synthetic"
PERTURBED_DIR = DATA_DIR / "synthetic_perturbed"
PROCESSED_DIR = DATA_DIR / "processed"
ARTIFACT_DIR = DATA_DIR / "artifacts"
REPORTS_DIR = REPO_ROOT / "reports"

DEMO_PERSONA_IDS = [f"C1000{i}" for i in range(1, 10)] + ["C10010"]
