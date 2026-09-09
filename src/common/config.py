"""Central configuration management for the customer support agent."""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW_DIR = DATA_DIR / "raw"
DATA_PROCESSED_DIR = DATA_DIR / "processed"
DATA_SAMPLE_DIR = DATA_DIR / "sample"
DATA_GOLDEN_DIR = DATA_DIR / "golden"

CONFIGS_DIR = PROJECT_ROOT / "configs"
RESULTS_DIR = PROJECT_ROOT / "results"
CACHE_DIR = PROJECT_ROOT / "cache"

# Ensure essential directories exist
for directory in [
    DATA_RAW_DIR,
    DATA_PROCESSED_DIR,
    DATA_SAMPLE_DIR,
    DATA_GOLDEN_DIR,
    CONFIGS_DIR,
    RESULTS_DIR,
    CACHE_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)

# LLM & Embedding configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_LLM_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Cache & Reproducibility
USE_CACHE = os.getenv("USE_CACHE", "true").lower() in ("true", "1", "yes")
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))
