"""Baseline intent classifiers: Majority Class and TF-IDF + Logistic Regression."""
from __future__ import annotations

import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Add project root to sys.path if run directly as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_recall_fscore_support,
    confusion_matrix,
    classification_report,
)

from src.common.config import DATA_PROCESSED_DIR, DATA_SAMPLE_DIR, DATA_GOLDEN_DIR, RANDOM_SEED
from src.taxonomy.taxonomy import default_taxonomy
from src.common.schemas import IntentPrediction


class MajorityClassBaseline:
    """Trivial Baseline: Always predicts the most frequent class."""

    def __init__(self, majority_intent: str = "SOFTWARE_UPDATE"):
        self.majority_intent = majority_intent

    def fit(self, texts: List[str], labels: List[str]) -> MajorityClassBaseline:
        from collections import Counter
        counts = Counter(labels)
        if counts:
            self.majority_intent = counts.most_common(1)[0][0]
        return self

    def predict(self, texts: List[str]) -> List[str]:
        return [self.majority_intent for _ in texts]

    def predict_one(self, text: str) -> IntentPrediction:
        return IntentPrediction(
            intent=self.majority_intent,
            confidence=0.10,  # 1 out of 10 classes
            reason=f"Trivial baseline: default majority class '{self.majority_intent}'",
        )


class TfidfLogisticBaseline:
    """Simple ML Baseline: TF-IDF n-grams + Logistic Regression."""

    def __init__(self, max_features: int = 4000, ngram_range: Tuple[int, int] = (1, 2)):
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            stop_words="english",
            sublinear_tf=True,
        )
        self.clf = LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=RANDOM_SEED,
            C=1.0,
        )
        self.is_fitted = False
        self.classes_ = default_taxonomy.get_intent_names()

    def fit(self, texts: List[str], labels: List[str]) -> TfidfLogisticBaseline:
        print(f"[Baseline ML] Training TF-IDF vectorizer and Logistic Regression on {len(texts):,} cases...")
        X = self.vectorizer.fit_transform(texts)
        self.clf.fit(X, labels)
        self.classes_ = list(self.clf.classes_)
        self.is_fitted = True
        return self

    def predict(self, texts: List[str]) -> List[str]:
        if not self.is_fitted:
            raise RuntimeError("Classifier not fitted.")
        X = self.vectorizer.transform(texts)
        return list(self.clf.predict(X))

    def predict_proba(self, texts: List[str]) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Classifier not fitted.")
        X = self.vectorizer.transform(texts)
        return self.clf.predict_proba(X)

    def predict_one(self, text: str) -> IntentPrediction:
        if not self.is_fitted:
            raise RuntimeError("Classifier not fitted.")
        X = self.vectorizer.transform([text])
        probs = self.clf.predict_proba(X)[0]
        best_idx = int(np.argmax(probs))
        best_class = self.classes_[best_idx]
        confidence = float(probs[best_idx])
        prob_dict = {cls: float(prob) for cls, prob in zip(self.classes_, probs)}

        return IntentPrediction(
            intent=best_class,
            confidence=round(confidence, 4),
            reason=f"TF-IDF Logistic Regression predicted {best_class} with probability {confidence:.2f}",
            probabilities=prob_dict,
        )


def evaluate_classifier_predictions(
    y_true: List[str],
    y_pred: List[str],
    labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compute comprehensive classification metrics."""
    if labels is None:
        labels = default_taxonomy.get_intent_names()

    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )

    per_class = {}
    for i, label in enumerate(labels):
        per_class[label] = {
            "precision": round(float(precision[i]), 4),
            "recall": round(float(recall[i]), 4),
            "f1": round(float(f1[i]), 4),
            "support": int(support[i]),
        }

    cm = confusion_matrix(y_true, y_pred, labels=labels).tolist()

    return {
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "per_class": per_class,
        "confusion_matrix": cm,
        "labels": labels,
    }


if __name__ == "__main__":
    print("=" * 75)
    print("BASELINE INTENT CLASSIFIER RUNNER: MAJORITY CLASS & TF-IDF + LOGISTIC")
    print("=" * 75)

    sample_queries = [
        "My iPhone 7 battery is draining from 100% to 10% in just two hours.",
        "My Apple ID has been locked for security reasons and I can't log in.",
        "I was charged $14.99 on my credit card for a subscription I canceled.",
        "Wi-Fi keeps disconnecting and Bluetooth won't pair with my headphones.",
    ]

    # Model 1: Majority Class Baseline
    print("\n--- Model 1: Majority Class Baseline ---")
    majority_clf = MajorityClassBaseline(majority_intent="SOFTWARE_UPDATE")
    for q in sample_queries:
        pred = majority_clf.predict_one(q)
        print(f"  Query: \"{q[:55]}...\"")
        print(f"  -> Predicted: {pred.intent} (Confidence: {pred.confidence:.2f})\n")

    # Model 2: TF-IDF + Logistic Regression Baseline
    print("--- Model 2: TF-IDF + Logistic Regression Baseline ---")
    golden_path = DATA_GOLDEN_DIR / "golden_set.jsonl"
    if golden_path.exists():
        with open(golden_path, "r", encoding="utf-8") as f:
            cases = [json.loads(line) for line in f if line.strip()]

        texts = [c["customer_message"] for c in cases]
        labels = [c["intent"] for c in cases]
        print(f"[Baseline] Training on {len(cases)} Golden Set cases across 10 classes...")

        tfidf_clf = TfidfLogisticBaseline()
        tfidf_clf.fit(texts, labels)

        print("\nPredictions on Sample Queries:")
        for q in sample_queries:
            pred = tfidf_clf.predict_one(q)
            print(f"  Query: \"{q[:55]}...\"")
            print(f"  -> Predicted: {pred.intent} (Confidence: {pred.confidence:.2f})\n")

        print("Evaluating Model 2 on Ground-Truth Golden Set:")
        eval_preds = tfidf_clf.predict(texts)
        metrics = evaluate_classifier_predictions(labels, eval_preds)
        print(f"  Accuracy:    {metrics['accuracy'] * 100:.2f}%")
        print(f"  Macro F1:    {metrics['macro_f1'] * 100:.2f}%")
        print(f"  Weighted F1: {metrics['weighted_f1'] * 100:.2f}%")
    else:
        print(f"[Warning] Golden set not found at {golden_path}")

    print("\n" + "=" * 75)
    print("[Success] Baseline classifier run completed successfully.")
    print("=" * 75)
