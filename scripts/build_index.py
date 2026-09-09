"""CLI script to build and serialize the FAISS historical support case index."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.retrieval.index import SupportCaseIndex
from src.common.config import DATA_SAMPLE_DIR


def main():
    sample_file = DATA_SAMPLE_DIR / "knowledge_base_sample.jsonl"
    print(f"[BuildIndex] Starting FAISS index construction from {sample_file}...")
    index_mgr = SupportCaseIndex()
    index_mgr.build_from_jsonl(jsonl_path=sample_file, save_after_build=True)
    print("[BuildIndex] Index construction and serialization completed successfully.")


if __name__ == "__main__":
    main()
