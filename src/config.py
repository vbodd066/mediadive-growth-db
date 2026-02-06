"""
Centralized configuration — reads from .env with sensible defaults.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ───────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = DATA_DIR / "models"
DB_PATH = Path(os.getenv("DB_PATH", str(DATA_DIR / "mediadive.db")))

# ── MediaDive API ───────────────────────────────────────────
BASE_URL = os.getenv("MEDIADIVE_BASE_URL", "https://mediadive.dsmz.de/rest")
REQUEST_DELAY = float(os.getenv("MEDIADIVE_REQUEST_DELAY", "0.5"))
TIMEOUT = int(os.getenv("MEDIADIVE_TIMEOUT", "30"))

# ── Logging ─────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ── Experiment tracking ─────────────────────────────────────
WANDB_PROJECT = os.getenv("WANDB_PROJECT", "mediadive-growth")

# ── Training defaults ───────────────────────────────────────
DEFAULT_SEED = 42
DEFAULT_TEST_SIZE = 0.15
DEFAULT_VAL_SIZE = 0.15
DEFAULT_BATCH_SIZE = 64
DEFAULT_LR = 1e-3
DEFAULT_EPOCHS = 100
