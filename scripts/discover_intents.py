"""Data-driven intent discovery via clustering and n-gram analysis."""
from __future__ import annotations

import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import MiniBatchKMeans

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from src.common.config import DATA_PROCESSED_DIR, RESULTS_DIR, RANDOM_SEED


def discover_intents_from_data(sample_size: int = 15000, n_clusters: int = 10):
    kb_path = DATA_PROCESSED_DIR / "knowledge_base.jsonl"
    print(f"[Discovery] Reading customer inquiries from {kb_path}...")
    texts = []
    with open(kb_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= sample_size:
                break
            record = json.loads(line)
            text = record.get("initial_customer_problem", "").strip()
            if len(text.split()) >= 4:
                texts.append(text)

    print(f"[Discovery] Analyzing {len(texts):,} customer problem inquiries...")

    # Vectorize with TF-IDF (1-gram and 2-grams)
    stop_words = "english"
    vectorizer = TfidfVectorizer(
        max_df=0.4,
        min_df=5,
        ngram_range=(1, 2),
        stop_words=stop_words,
        max_features=5000,
    )
    X = vectorizer.fit_transform(texts)
    feature_names = vectorizer.get_feature_names_out()

    print(f"[Discovery] Fitting {n_clusters} clusters with MiniBatchKMeans...")
    kmeans = MiniBatchKMeans(n_clusters=n_clusters, random_state=RANDOM_SEED, batch_size=1024, n_init="auto")
    labels = kmeans.fit_predict(X)

    # Order cluster centers by proximity to centroid
    order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]

    discovery_results = []
    print("\n" + "=" * 75)
    print("EMPIRICAL CLUSTER DISCOVERY RESULTS")
    print("=" * 75)

    for cluster_id in range(n_clusters):
        top_terms = [feature_names[ind] for ind in order_centroids[cluster_id, :12]]
        cluster_indices = np.where(labels == cluster_id)[0]
        cluster_pct = (len(cluster_indices) / len(texts)) * 100
        
        # Sample 4 real customer tweets from this cluster
        sample_texts = [texts[idx] for idx in cluster_indices[:4]]
        
        cluster_summary = {
            "cluster_id": cluster_id,
            "size": len(cluster_indices),
            "percentage": round(cluster_pct, 2),
            "top_terms": top_terms,
            "sample_texts": sample_texts,
        }
        discovery_results.append(cluster_summary)

        print(f"\n[Cluster {cluster_id + 1}] ({cluster_pct:.1f}% of inquiries)")
        print(f"  Key Terms: {', '.join(top_terms)}")
        print("  Sample Customer Inquiries:")
        for s in sample_texts:
            clean_s = s.encode("ascii", errors="replace").decode("ascii")
            print(f"    - \"{clean_s}\"")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "discovered_clusters.json", "w", encoding="utf-8") as f:
        json.dump(discovery_results, f, indent=2)

    print(f"\n[Discovery] Cluster analysis saved to {RESULTS_DIR / 'discovered_clusters.json'}")
    return discovery_results


if __name__ == "__main__":
    discover_intents_from_data()
