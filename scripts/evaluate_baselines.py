"""Benchmark and compare Intent Classification Baselines vs Main Classifier on Golden Set."""
from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.common.config import DATA_SAMPLE_DIR, DATA_GOLDEN_DIR, RESULTS_DIR
from src.taxonomy.taxonomy import default_taxonomy
from src.classifier.baseline import MajorityClassBaseline, TfidfLogisticBaseline, evaluate_classifier_predictions
from src.classifier.classifier import default_classifier


def run_baseline_comparison():
    print("=" * 75)
    print("INTENT CLASSIFIER BENCHMARK: BASELINES VS MAIN CLASSIFIER")
    print("=" * 75)

    # 1. Load 200 Golden Set ground-truth cases
    golden_path = DATA_GOLDEN_DIR / "golden_set.jsonl"
    golden_cases = []
    with open(golden_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                golden_cases.append(json.loads(line))

    y_test_true = [c["intent"] for c in golden_cases]
    test_texts = [c["customer_message"] for c in golden_cases]
    print(f"[Benchmark] Loaded {len(golden_cases)} ground-truth Golden Set evaluation cases.")

    # 2. Prepare training data for Simple ML Baseline (TF-IDF + Logistic Regression)
    # Use 2,500 historical cases from knowledge_base_sample.jsonl
    sample_path = DATA_SAMPLE_DIR / "knowledge_base_sample.jsonl"
    train_texts = []
    with open(sample_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 2500:
                break
            train_texts.append(json.loads(line)["initial_customer_problem"])

    print(f"[Benchmark] Silver-labeling {len(train_texts):,} historical training cases with semantic classifier...")
    train_preds = default_classifier.predict_batch(train_texts)
    train_labels = [p.intent for p in train_preds]

    # Model 1: Majority Class Baseline
    print("\n--- Evaluating Baseline 1: Majority Class ---")
    majority_model = MajorityClassBaseline().fit(train_texts, train_labels)
    majority_preds = majority_model.predict(test_texts)
    majority_metrics = evaluate_classifier_predictions(y_test_true, majority_preds)
    print(f"  Accuracy:  {majority_metrics['accuracy'] * 100:.2f}%")
    print(f"  Macro F1:  {majority_metrics['macro_f1'] * 100:.2f}%")
    print(f"  Weighted:  {majority_metrics['weighted_f1'] * 100:.2f}%")

    # Model 2: TF-IDF + Logistic Regression Baseline
    print("\n--- Evaluating Baseline 2: TF-IDF + Logistic Regression ---")
    tfidf_model = TfidfLogisticBaseline()
    tfidf_model.fit(train_texts, train_labels)
    tfidf_preds = tfidf_model.predict(test_texts)
    tfidf_metrics = evaluate_classifier_predictions(y_test_true, tfidf_preds)
    print(f"  Accuracy:  {tfidf_metrics['accuracy'] * 100:.2f}%")
    print(f"  Macro F1:  {tfidf_metrics['macro_f1'] * 100:.2f}%")
    print(f"  Weighted:  {tfidf_metrics['weighted_f1'] * 100:.2f}%")

    # Model 3: Main Classifier (Dense Semantic Centroid)
    print("\n--- Evaluating Main Classifier: Dense Semantic Centroid ---")
    main_preds_objects = default_classifier.predict_batch(test_texts)
    main_preds = [p.intent for p in main_preds_objects]
    main_metrics = evaluate_classifier_predictions(y_test_true, main_preds)
    print(f"  Accuracy:  {main_metrics['accuracy'] * 100:.2f}%")
    print(f"  Macro F1:  {main_metrics['macro_f1'] * 100:.2f}%")
    print(f"  Weighted:  {main_metrics['weighted_f1'] * 100:.2f}%")

    # Comparative Summary Table
    comparison_summary = {
        "Majority_Baseline": {
            "accuracy": majority_metrics["accuracy"],
            "macro_f1": majority_metrics["macro_f1"],
            "weighted_f1": majority_metrics["weighted_f1"],
        },
        "TFIDF_Logistic_Baseline": {
            "accuracy": tfidf_metrics["accuracy"],
            "macro_f1": tfidf_metrics["macro_f1"],
            "weighted_f1": tfidf_metrics["weighted_f1"],
        },
        "Main_Semantic_Classifier": {
            "accuracy": main_metrics["accuracy"],
            "macro_f1": main_metrics["macro_f1"],
            "weighted_f1": main_metrics["weighted_f1"],
        },
        "per_class_main": main_metrics["per_class"],
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / "classifier_baselines_comparison.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(comparison_summary, f, indent=2)

    print("\n" + "=" * 75)
    print(f"{'Model':<30} | {'Accuracy':<10} | {'Macro F1':<10} | {'Weighted F1':<12}")
    print("-" * 75)
    print(f"{'1. Majority Class':<30} | {majority_metrics['accuracy']*100:<9.1f}% | {majority_metrics['macro_f1']*100:<9.1f}% | {majority_metrics['weighted_f1']*100:<11.1f}%")
    print(f"{'2. TF-IDF + Logistic Reg':<30} | {tfidf_metrics['accuracy']*100:<9.1f}% | {tfidf_metrics['macro_f1']*100:<9.1f}% | {tfidf_metrics['weighted_f1']*100:<11.1f}%")
    print(f"{'3. Main Semantic Classifier':<30} | {main_metrics['accuracy']*100:<9.1f}% | {main_metrics['macro_f1']*100:<9.1f}% | {main_metrics['weighted_f1']*100:<11.1f}%")
    print("=" * 75)

    print("\n--- PER-INTENT METRICS (MAIN CLASSIFIER) ---")
    print(f"{'Intent':<24} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10}")
    print("-" * 62)
    for intent, p_dict in main_metrics["per_class"].items():
        print(f"{intent:<24} | {p_dict['precision']*100:<9.1f}% | {p_dict['recall']*100:<9.1f}% | {p_dict['f1']*100:<9.1f}%")

    print(f"\n[Benchmark] Results saved to {out_file}")
    return comparison_summary


if __name__ == "__main__":
    run_baseline_comparison()
