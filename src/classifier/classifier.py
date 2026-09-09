"""Main Intent Classifier: High-performance semantic embedding similarity + LLM hybrid."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from sentence_transformers import SentenceTransformer
from src.common.config import DEFAULT_EMBEDDING_MODEL, RANDOM_SEED
from src.taxonomy.taxonomy import default_taxonomy
from src.common.schemas import IntentPrediction
from src.common.llm import default_llm_client


class SemanticIntentClassifier:
    """Zero-shot / Few-shot dense semantic intent classifier using sentence embeddings.

    Computes cosine similarity between incoming customer text and taxonomy exemplar centroids.
    Converts similarities into calibrated probability distributions with temperature softmax.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        abstain_threshold: float = 0.30,
        temperature: float = 0.15,
    ):
        self.model_name = model_name
        self.abstain_threshold = abstain_threshold
        self.temperature = temperature
        print(f"[Classifier] Initializing embedding model: {model_name}...")
        self.encoder = SentenceTransformer(model_name)
        self.intents = default_taxonomy.get_intent_names()
        self._exemplar_embeddings: Optional[np.ndarray] = None
        self._intent_centroids: Optional[Dict[str, np.ndarray]] = None
        self._build_taxonomy_index()

    def _build_taxonomy_index(self) -> None:
        """Encode intent definitions and positive examples into exemplar centroids."""
        print("[Classifier] Building taxonomy exemplar embeddings...")
        centroids = {}
        for intent in self.intents:
            info = default_taxonomy.get_intent_info(intent)
            # Combine intent name, description, and positive examples
            texts_to_embed = [f"{intent}: {info['description']}"] + info.get("positive_examples", [])
            embeddings = self.encoder.encode(texts_to_embed, convert_to_numpy=True, normalize_embeddings=True)
            # Mean pooling to form intent centroid
            centroid = np.mean(embeddings, axis=0)
            centroid = centroid / np.linalg.norm(centroid)
            centroids[intent] = centroid

        self._intent_centroids = centroids
        self._centroid_matrix = np.array([centroids[intent] for intent in self.intents])  # shape: (10, dim)
        print(f"[Classifier] Indexed {len(self.intents)} intent centroids.")

    def predict_one(self, text: str) -> IntentPrediction:
        """Classify a single customer message."""
        if not text or not text.strip():
            return IntentPrediction(
                intent="OUT_OF_SCOPE",
                confidence=0.0,
                reason="Empty or whitespace query; cannot classify.",
            )

        # Encode input text
        query_emb = self.encoder.encode([text], convert_to_numpy=True, normalize_embeddings=True)[0]

        # Cosine similarity against all centroids (since normalized, dot product = cosine sim)
        sims = np.dot(self._centroid_matrix, query_emb)  # shape: (10,)

        # Temperature softmax for calibrated probabilities
        exp_sims = np.exp((sims - np.max(sims)) / self.temperature)
        probs = exp_sims / np.sum(exp_sims)

        best_idx = int(np.argmax(probs))
        best_intent = self.intents[best_idx]
        best_prob = float(probs[best_idx])
        raw_sim = float(sims[best_idx])

        prob_dict = {intent: round(float(p), 4) for intent, p in zip(self.intents, probs)}

        # Abstention check: if raw semantic similarity is too weak, abstain
        if raw_sim < self.abstain_threshold:
            return IntentPrediction(
                intent="OUT_OF_SCOPE",
                confidence=round(best_prob, 4),
                reason=f"Abstention: semantic similarity ({raw_sim:.2f}) below threshold ({self.abstain_threshold:.2f})",
                probabilities=prob_dict,
            )

        info = default_taxonomy.get_intent_info(best_intent)
        reason = (
            f"Classified as '{best_intent}' ({info['name']}) with semantic similarity {raw_sim:.2f} "
            f"and calibrated confidence {best_prob:.2f}"
        )

        return IntentPrediction(
            intent=best_intent,
            confidence=round(best_prob, 4),
            reason=reason,
            probabilities=prob_dict,
        )

    def predict_batch(self, texts: List[str]) -> List[IntentPrediction]:
        """Classify a batch of customer messages with vectorized embedding."""
        if not texts:
            return []

        embeddings = self.encoder.encode(texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
        sim_matrix = np.dot(embeddings, self._centroid_matrix.T)  # shape: (N, 10)

        predictions = []
        for i, text in enumerate(texts):
            sims = sim_matrix[i]
            exp_sims = np.exp((sims - np.max(sims)) / self.temperature)
            probs = exp_sims / np.sum(exp_sims)
            best_idx = int(np.argmax(probs))
            best_intent = self.intents[best_idx]
            best_prob = float(probs[best_idx])
            raw_sim = float(sims[best_idx])
            prob_dict = {intent: round(float(p), 4) for intent, p in zip(self.intents, probs)}

            if raw_sim < self.abstain_threshold:
                pred = IntentPrediction(
                    intent="OUT_OF_SCOPE",
                    confidence=round(best_prob, 4),
                    reason=f"Abstention: low similarity ({raw_sim:.2f})",
                    probabilities=prob_dict,
                )
            else:
                pred = IntentPrediction(
                    intent=best_intent,
                    confidence=round(best_prob, 4),
                    reason=f"Semantic similarity {raw_sim:.2f}",
                    probabilities=prob_dict,
                )
            predictions.append(pred)

        return predictions


# Singleton instance
default_classifier = SemanticIntentClassifier()
