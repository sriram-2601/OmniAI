"""FAISS index construction and persistence for historical support cases."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import faiss
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

from src.common.config import DATA_PROCESSED_DIR, DATA_SAMPLE_DIR, DEFAULT_EMBEDDING_MODEL
from src.common.schemas import SupportCase


INDEX_FILE_PATH = DATA_PROCESSED_DIR / "faiss_index.bin"
METADATA_FILE_PATH = DATA_PROCESSED_DIR / "faiss_metadata.json"


class SupportCaseIndex:
    """FAISS vector index manager for historical customer support cases."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL):
        self.model_name = model_name
        self.encoder = SentenceTransformer(model_name)
        self.dimension = (
            self.encoder.get_embedding_dimension()
            if hasattr(self.encoder, "get_embedding_dimension")
            else self.encoder.get_sentence_embedding_dimension()
        )
        self.index: Optional[faiss.IndexFlatIP] = None
        self.cases_metadata: List[Dict[str, Any]] = []

    def build_from_jsonl(
        self,
        jsonl_path: Path = DATA_SAMPLE_DIR / "knowledge_base_sample.jsonl",
        save_after_build: bool = True,
        batch_size: int = 256,
    ) -> SupportCaseIndex:
        """Build FAISS index from historical support cases."""
        jsonl_path = Path(jsonl_path)
        print(f"[Index] Reading support cases from {jsonl_path}...")

        cases = []
        texts_to_embed = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    cases.append(item)
                    # Embed customer inquiry for symmetric semantic retrieval
                    text = item.get("initial_customer_problem", "").strip()
                    texts_to_embed.append(text)

        print(f"[Index] Loaded {len(cases):,} cases. Generating dense embeddings on CPU...")
        embeddings = self.encoder.encode(
            texts_to_embed,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

        print(f"[Index] Building FAISS IndexFlatIP (dim={self.dimension})...")
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings)
        self.cases_metadata = cases

        print(f"[Index] Successfully indexed {self.index.ntotal:,} support cases.")

        if save_after_build:
            self.save()

        return self

    def save(
        self,
        index_path: Path = INDEX_FILE_PATH,
        metadata_path: Path = METADATA_FILE_PATH,
    ) -> None:
        """Persist index and metadata to disk."""
        if self.index is None:
            raise RuntimeError("Cannot save an empty index.")
        index_path = Path(index_path)
        metadata_path = Path(metadata_path)
        index_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"[Index] Writing FAISS binary to {index_path}...")
        faiss.write_index(self.index, str(index_path))

        print(f"[Index] Writing metadata JSON to {metadata_path}...")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.cases_metadata, f, ensure_ascii=False)

        print("[Index] Index and metadata saved successfully.")

    def load(
        self,
        index_path: Path = INDEX_FILE_PATH,
        metadata_path: Path = METADATA_FILE_PATH,
    ) -> SupportCaseIndex:
        """Load persisted index and metadata from disk."""
        index_path = Path(index_path)
        metadata_path = Path(metadata_path)

        if not index_path.exists() or not metadata_path.exists():
            raise FileNotFoundError(f"Missing index or metadata at {index_path} / {metadata_path}")

        print(f"[Index] Loading FAISS index from {index_path}...")
        self.index = faiss.read_index(str(index_path))

        print(f"[Index] Loading metadata from {metadata_path}...")
        with open(metadata_path, "r", encoding="utf-8") as f:
            self.cases_metadata = json.load(f)

        print(f"[Index] Loaded {self.index.ntotal:,} indexed cases.")
        return self
