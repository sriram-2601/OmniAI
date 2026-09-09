"""Baseline intent classifiers: Majority Class and TF-IDF + Logistic Regression."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
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
