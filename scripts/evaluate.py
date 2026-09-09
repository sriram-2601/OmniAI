"""Master Evaluation Suite: End-to-End Benchmark across all 200 Golden Set Examples.

Executes the complete production support agent pipeline, computing:
1. Intent Classification Metrics (Accuracy, Macro F1, Per-intent breakdown, Confusion Matrix PNG)
2. Historical Precedent Retrieval Metrics (Hit@1, Hit@3, Hit@5, MRR, Mean Similarity)
3. Safety-First Escalation Metrics (Coverage, Auto Precision, False Auto-Handling Rate)
4. LLM-as-a-Judge Quality Scores (Correctness, Grounding, Helpfulness, Safety, Brand Fit)
5. Human-Judge Calibration (Spearman rho, Pearson r, Cohen's kappa, MAE)
6. Failure Categorization (Top 5 failure modes with real examples)
"""
from __future__ import annotations

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.common.config import DATA_GOLDEN_DIR, RESULTS_DIR
from src.taxonomy.taxonomy import default_taxonomy
from src.agent import default_agent
from src.evaluation.judge import default_judge
from src.evaluation.escalation import compute_escalation_metrics
from src.evaluation.calibration import calibrate_sample_pairs
from src.evaluation.failure_analysis import analyze_failures


def run_full_evaluation():
    print("=" * 80)
    print("MASTER EVALUATION BENCHMARK: FULL SUPPORT AGENT ON 200 GOLDEN CASES")
    print("=" * 80)

    # 1. Load 200 Golden Set Ground-Truth Cases
    golden_path = DATA_GOLDEN_DIR / "golden_set.jsonl"
    golden_cases = []
    with open(golden_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                golden_cases.append(json.loads(line))

    n_cases = len(golden_cases)
    print(f"[Eval] Loaded {n_cases} ground-truth cases from {golden_path.name}")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    y_true_intent = []
    y_pred_intent = []
    y_conf_intent = []

    y_true_action = []
    y_pred_action = []
    risk_levels = []

    retrieval_hit1 = []
    retrieval_hit3 = []
    retrieval_hit5 = []
    reciprocal_ranks = []
    top1_similarities = []

    judge_records = []
    latencies = []
    eval_records = []

    print(f"[Eval] Running agent inference and evaluation across {n_cases} cases...")
    start_eval_time = time.perf_counter()

    for idx, case in enumerate(golden_cases, 1):
        cid = case["id"]
        msg = case["customer_message"]
        exp_intent = case["intent"]
        exp_action = case["expected_action"]
        exp_risk = case.get("risk_level", "LOW")

        # Step 1: Agent Pipeline Execution
        out = default_agent.process_message(msg, exclude_case_id=cid)
        latencies.append(out.latency_ms)

        pred_intent = out.intent.intent
        conf = out.intent.confidence
        act_action = out.decision.decision
        act_risk = out.risk.level

        y_true_intent.append(exp_intent)
        y_pred_intent.append(pred_intent)
        y_conf_intent.append(conf)

        y_true_action.append(exp_action)
        y_pred_action.append(act_action)
        risk_levels.append(act_risk)

        # Step 2: Retrieval Evaluation
        # Check top-5 retrieved items against query ground-truth intent
        raw_retrieved = default_agent.retriever.retrieve(msg, top_k=5, exclude_case_id=cid)
        if raw_retrieved:
            top1_similarities.append(raw_retrieved[0].similarity_score)
            found_hit = False
            first_hit_rank = 0

            # Evaluate intent alignment of retrieved historical inquiries
            for rank, item in enumerate(raw_retrieved, 1):
                item_intent = default_agent.classifier.predict_one(item.customer_message).intent
                if item_intent == exp_intent:
                    if not found_hit:
                        first_hit_rank = rank
                        found_hit = True

            retrieval_hit1.append(1 if first_hit_rank == 1 else 0)
            retrieval_hit3.append(1 if 1 <= first_hit_rank <= 3 else 0)
            retrieval_hit5.append(1 if 1 <= first_hit_rank <= 5 else 0)
            reciprocal_ranks.append(1.0 / first_hit_rank if found_hit else 0.0)
        else:
            top1_similarities.append(0.0)
            retrieval_hit1.append(0)
            retrieval_hit3.append(0)
            retrieval_hit5.append(0)
            reciprocal_ranks.append(0.0)

        # Step 3: Judge Evaluation
        judge_res = default_judge.judge_reply(
            customer_message=msg,
            draft_reply=out.draft_reply,
            intent=pred_intent,
            decision=act_action,
            evidence=out.evidence,
        )
        judge_records.append(judge_res)

        eval_rec = {
            "id": cid,
            "customer_message": msg,
            "expected_intent": exp_intent,
            "predicted_intent": pred_intent,
            "intent_confidence": round(conf, 4),
            "intent_correct": (exp_intent == pred_intent),
            "expected_action": exp_action,
            "actual_decision": act_action,
            "action_correct": (exp_action == act_action),
            "risk_level": act_risk,
            "risk_factors": out.risk.risk_factors,
            "escalation_reason": out.decision.reason,
            "draft_reply": out.draft_reply,
            "reply_length": len(out.draft_reply),
            "evidence_count": len(out.evidence),
            "top_precedent_case_id": out.evidence[0].case_id if out.evidence else None,
            "latency_ms": out.latency_ms,
            "judge_overall": judge_res["overall"],
            "judge_correctness": judge_res["correctness"],
            "judge_grounding": judge_res["historical_grounding"],
            "judge_helpfulness": judge_res["helpfulness"],
            "judge_safety": judge_res["safety"],
            "judge_brand_fit": judge_res["brand_fit"],
            "judge_reason": judge_res["reason"],
        }
        eval_records.append(eval_rec)

        if idx % 50 == 0 or idx == n_cases:
            print(f"  Processed {idx}/{n_cases} cases ({idx / n_cases * 100:.0f}%)...")

    total_eval_duration = time.perf_counter() - start_eval_time
    print(f"[Eval] Completed 200 cases in {total_eval_duration:.2f}s ({total_eval_duration/n_cases*1000:.1f} ms/case)")

    # -------------------------------------------------------------
    # 1. Classification Metrics
    # -------------------------------------------------------------
    intent_labels = default_taxonomy.intent_names
    acc = accuracy_score(y_true_intent, y_pred_intent)
    prec_m, rec_m, f1_m, _ = precision_recall_fscore_support(
        y_true_intent, y_pred_intent, average="macro", zero_division=0
    )
    prec_w, rec_w, f1_w, _ = precision_recall_fscore_support(
        y_true_intent, y_pred_intent, average="weighted", zero_division=0
    )

    clf_report = classification_report(
        y_true_intent, y_pred_intent, labels=intent_labels, output_dict=True, zero_division=0
    )
    with open(RESULTS_DIR / "classification_report.json", "w", encoding="utf-8") as f:
        json.dump(clf_report, f, indent=2)

    # Confusion Matrix Visualization
    cm = confusion_matrix(y_true_intent, y_pred_intent, labels=intent_labels)
    plt.figure(figsize=(11, 9))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=[l.replace("_", "\n") for l in intent_labels],
        yticklabels=intent_labels,
        cbar=True,
    )
    plt.title("Intent Classification Confusion Matrix (200 Golden Set Cases)", fontsize=13, pad=15)
    plt.xlabel("Predicted Intent", fontsize=11, labelpad=10)
    plt.ylabel("Ground Truth Intent", fontsize=11, labelpad=10)
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.yticks(rotation=0, fontsize=9)
    plt.tight_layout()
    cm_path = RESULTS_DIR / "confusion_matrix.png"
    plt.savefig(cm_path, dpi=200)
    plt.close()
    print(f"[Output] Saved confusion matrix visualization to {cm_path.name}")

    # -------------------------------------------------------------
    # 2. Retrieval Metrics
    # -------------------------------------------------------------
    ret_hit1 = float(np.mean(retrieval_hit1)) * 100.0
    ret_hit3 = float(np.mean(retrieval_hit3)) * 100.0
    ret_hit5 = float(np.mean(retrieval_hit5)) * 100.0
    mrr = float(np.mean(reciprocal_ranks))
    mean_sim = float(np.mean(top1_similarities))

    # -------------------------------------------------------------
    # 3. Escalation & Safety Metrics
    # -------------------------------------------------------------
    esc_metrics = compute_escalation_metrics(y_true_action, y_pred_action, risk_levels)
    with open(RESULTS_DIR / "escalation_metrics.json", "w", encoding="utf-8") as f:
        json.dump(esc_metrics, f, indent=2)

    # -------------------------------------------------------------
    # 4. Reply Quality Metrics (Judge)
    # -------------------------------------------------------------
    mean_correctness = float(np.mean([r["correctness"] for r in judge_records]))
    mean_grounding = float(np.mean([r["historical_grounding"] for r in judge_records]))
    mean_helpfulness = float(np.mean([r["helpfulness"] for r in judge_records]))
    mean_safety = float(np.mean([r["safety"] for r in judge_records]))
    mean_brand_fit = float(np.mean([r["brand_fit"] for r in judge_records]))
    mean_overall = float(np.mean([r["overall"] for r in judge_records]))

    reply_quality_summary = {
        "mean_correctness": round(mean_correctness, 2),
        "mean_historical_grounding": round(mean_grounding, 2),
        "mean_helpfulness": round(mean_helpfulness, 2),
        "mean_safety": round(mean_safety, 2),
        "mean_brand_fit": round(mean_brand_fit, 2),
        "mean_overall": round(mean_overall, 2),
        "sample_evaluations": eval_records[:10],
    }
    with open(RESULTS_DIR / "reply_scores.json", "w", encoding="utf-8") as f:
        json.dump(reply_quality_summary, f, indent=2)

    # -------------------------------------------------------------
    # 5. Judge Calibration & Human Agreement
    # -------------------------------------------------------------
    calibration_metrics = calibrate_sample_pairs(eval_records, n_samples=50)

    # -------------------------------------------------------------
    # 6. Failure Analysis
    # -------------------------------------------------------------
    failure_report = analyze_failures(eval_records)

    # -------------------------------------------------------------
    # 7. Consolidated Metrics Summary
    # -------------------------------------------------------------
    summary_metrics = {
        "dataset": "AppleSupport Holdout Benchmark (200 Curated Cases)",
        "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_cases": n_cases,
        "classification": {
            "accuracy": round(acc * 100.0, 2),
            "macro_precision": round(prec_m * 100.0, 2),
            "macro_recall": round(rec_m * 100.0, 2),
            "macro_f1": round(f1_m * 100.0, 2),
            "weighted_f1": round(f1_w * 100.0, 2),
        },
        "retrieval": {
            "hit_at_1_pct": round(ret_hit1, 2),
            "hit_at_3_pct": round(ret_hit3, 2),
            "hit_at_5_pct": round(ret_hit5, 2),
            "mrr": round(mrr, 4),
            "mean_top1_cosine_similarity": round(mean_sim, 4),
        },
        "escalation_safety": {
            "coverage_pct": esc_metrics["coverage_percentage"],
            "auto_handling_precision": esc_metrics["auto_handling_precision"],
            "auto_handling_recall": esc_metrics["auto_handling_recall"],
            "escalation_precision": esc_metrics["escalation_precision"],
            "escalation_recall": esc_metrics["escalation_recall"],
            "false_auto_handling_rate": esc_metrics["false_auto_handling_rate"],
            "dangerous_auto_count": esc_metrics["dangerous_auto_count"],
        },
        "reply_quality": {
            "overall": round(mean_overall, 2),
            "correctness": round(mean_correctness, 2),
            "historical_grounding": round(mean_grounding, 2),
            "helpfulness": round(mean_helpfulness, 2),
            "safety": round(mean_safety, 2),
            "brand_fit": round(mean_brand_fit, 2),
        },
        "judge_calibration": {
            "spearman_correlation": calibration_metrics["spearman_correlation"],
            "pearson_correlation": calibration_metrics["pearson_correlation"],
            "mean_absolute_error": calibration_metrics["mean_absolute_error"],
            "quadratic_weighted_kappa": calibration_metrics["quadratic_weighted_kappa"],
            "near_agreement_pct": calibration_metrics["near_agreement_pct_within_half_point"],
        },
        "latency_ms": {
            "mean": round(float(np.mean(latencies)), 2),
            "median": round(float(np.median(latencies)), 2),
            "p95": round(float(np.percentile(latencies, 95)), 2),
        },
        "failures": {
            "total_detected": failure_report["total_failures_detected"],
            "top_modes_count": len(failure_report["top_failure_modes"]),
        }
    }

    with open(RESULTS_DIR / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(summary_metrics, f, indent=2)

    # -------------------------------------------------------------
    # Print Beautiful Terminal Summary
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print("                      EVALUATION RESULTS SUMMARY")
    print("=" * 80)
    print(f"Total Evaluated: {n_cases} cases | Total Latency: {total_eval_duration:.2f}s | Avg Latency: {np.mean(latencies):.1f} ms/query")
    print("-" * 80)
    print("1. INTENT CLASSIFICATION (10 Taxonomy Classes):")
    print(f"   - Accuracy:         {summary_metrics['classification']['accuracy']}%")
    print(f"   - Macro F1:         {summary_metrics['classification']['macro_f1']}%")
    print(f"   - Weighted F1:      {summary_metrics['classification']['weighted_f1']}%")
    print("-" * 80)
    print("2. HISTORICAL PRECEDENT RETRIEVAL (5,000 FAISS Index):")
    print(f"   - Hit@1:            {summary_metrics['retrieval']['hit_at_1_pct']}%")
    print(f"   - Hit@3:            {summary_metrics['retrieval']['hit_at_3_pct']}%")
    print(f"   - Hit@5:            {summary_metrics['retrieval']['hit_at_5_pct']}%")
    print(f"   - MRR:              {summary_metrics['retrieval']['mrr']}")
    print(f"   - Mean Top-1 Sim:   {summary_metrics['retrieval']['mean_top1_cosine_similarity']}")
    print("-" * 80)
    print("3. SAFETY-CRITICAL ROUTING & ESCALATION:")
    print(f"   - Coverage (Auto):  {summary_metrics['escalation_safety']['coverage_pct']}% ({esc_metrics['auto_handled_count']}/{n_cases})")
    print(f"   - Auto Precision:   {summary_metrics['escalation_safety']['auto_handling_precision'] * 100:.1f}%")
    print(f"   - Esc Recall:       {summary_metrics['escalation_safety']['escalation_recall'] * 100:.1f}%")
    print(f"   - False Auto Rate:  {summary_metrics['escalation_safety']['false_auto_handling_rate'] * 100:.2f}% (CRITICAL SAFETY METRIC)")
    print(f"   - Dangerous Autos:  {summary_metrics['escalation_safety']['dangerous_auto_count']}")
    print("-" * 80)
    print("4. REPLY QUALITY & GROUNDING (1-5 Scale):")
    print(f"   - Overall Score:    {summary_metrics['reply_quality']['overall']} / 5.0")
    print(f"   - Correctness:      {summary_metrics['reply_quality']['correctness']} / 5.0")
    print(f"   - Grounding:        {summary_metrics['reply_quality']['historical_grounding']} / 5.0")
    print(f"   - Safety:           {summary_metrics['reply_quality']['safety']} / 5.0")
    print(f"   - Brand Fit:        {summary_metrics['reply_quality']['brand_fit']} / 5.0")
    print("-" * 80)
    print("5. JUDGE CALIBRATION & AGREEMENT:")
    print(f"   - Spearman rho:     {summary_metrics['judge_calibration']['spearman_correlation']}")
    print(f"   - Cohen's Kappa:    {summary_metrics['judge_calibration']['quadratic_weighted_kappa']}")
    print(f"   - MAE vs Human:     {summary_metrics['judge_calibration']['mean_absolute_error']} points")
    print("=" * 80)
    print(f"[Done] All outputs written to {RESULTS_DIR.resolve()}")
    return summary_metrics


if __name__ == "__main__":
    run_full_evaluation()
