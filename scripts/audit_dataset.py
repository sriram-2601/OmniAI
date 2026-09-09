"""CLI runner for dataset audit."""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.audit import run_dataset_audit

if __name__ == "__main__":
    print("[Runner] Starting dataset acquisition and audit...")
    audit_data = run_dataset_audit()
    print("[Runner] Dataset audit completed successfully.")
