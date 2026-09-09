# 🍎 @AppleSupport Enterprise AI Support Agent

> **Hiver SDE Intern Take-Home Assignment Submission**  
> An evidence-grounded, safety-first AI support agent built on 106,860 real `@AppleSupport` customer conversations from the Kaggle *Customer Support on Twitter* dataset.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests Passing](https://img.shields.io/badge/pytest-34%20passed-success.svg)](#run-test-suite)
[![Macro F1](https://img.shields.io/badge/Intent%20Macro%20F1-64.59%25-brightgreen.svg)](#headline-benchmark-results)
[![Auto-Handling Precision](https://img.shields.io/badge/Auto%20Precision-100.0%25-success.svg)](#headline-benchmark-results)
[![False Auto Rate](https://img.shields.io/badge/False%20Auto%20Rate-0.00%25-success.svg)](#headline-benchmark-results)
[![Latency](https://img.shields.io/badge/CPU%20Latency-47.6%20ms-informational.svg)](#headline-benchmark-results)

---

## ⚡ 30-Second Elevator Pitch

Most customer service bots fail in production because they prioritize aggressive automation over safety, hallucinating policies or exposing sensitive credentials on public feeds.

This system takes a fundamentally different engineering approach: **evidence-first, safety-first**.
1. **Empirical Intent Taxonomy:** Classifies incoming inquiries across 10 data-derived intent categories (`configs/intents.yaml`).
2. **FAISS Precedent Grounding:** Retrieves verified historical resolutions from a 5,000-case local vector database in $<4\text{ ms}$.
3. **Deterministic Safety Gating:** Hard-escalates financial disputes, credential resets, and physical battery hazards with zero hallucination risk.
4. **Grounded Generation:** Drafts concise, empathetic replies strictly under 280 characters matching historical Apple Support tone.
5. **Radical Intellectual Honesty:** Benchmarked against a hand-labelled 200-case Golden Set with human calibration and full failure mode auditing.

---

## 📊 Headline Benchmark Results (200 Curated Golden Set Cases)

| Dimension | Metric | Score | Baseline / Benchmark Context |
| :--- | :--- | :--- | :--- |
| **Intent Classification** | **Macro F1** | **64.59%** | vs. **1.82%** Majority Baseline, **67.40%** TF-IDF Baseline |
| **Intent Classification** | **Accuracy** | **65.00%** | vs. **10.00%** Majority Baseline (10 balanced classes) |
| **Precedent Retrieval** | **Hit@1** | **58.00%** | Fraction where top-1 precedent matches ground-truth intent |
| **Precedent Retrieval** | **Hit@3** | **73.00%** | Fraction where top-3 precedents match ground-truth intent |
| **Precedent Retrieval** | **Hit@5** | **79.00%** | Fraction where top-5 precedents match ground-truth intent |
| **Precedent Retrieval** | **MRR** | **0.6595** | Mean Reciprocal Rank across 5,000 indexed cases |
| **Escalation Safety** | **Auto-Handling Precision** | **100.0%** | **17 / 17 automated cases were safe and accurate** |
| **Escalation Safety** | **Escalation Recall** | **100.0%** | **Caught 100% of cases requiring human handling** |
| **Escalation Safety** | **False Auto-Handling Rate** | **0.00%** | **CRITICAL SAFETY METRIC: Zero unsafe automated replies** |
| **Escalation Safety** | **Dangerous Autos** | **0** | Zero credential or billing disputes automated |
| **Automation Coverage** | **Coverage %** | **8.50%** | Conservative safety triage threshold |
| **Reply Quality** | **LLM-Judge Overall** | **4.70 / 5.0** | Correctness: 4.78, Grounding: 4.77, Safety: 4.96 |
| **Inference Latency** | **Mean Latency (CPU)** | **47.6 ms** | P95: 64.4 ms, P50: 45.5 ms (Standard CPU, zero GPU needed) |

*Full analysis, confusion matrices, and calibration details are documented in [`REPORT.md`](file:///c:/Users/srira/Desktop/pro/new-twitter-pro/REPORT.md).*

---

## 🏗️ Architecture Diagram

```
                             [ Incoming Customer Tweet ]
                                          │
                                          ▼
                         ┌─────────────────────────────────┐
                         │   Sanitization & PII Masking    │
                         └────────────────┬────────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
   ┌─────────────────────────────┐                 ┌─────────────────────────────┐
   │  Semantic Intent Classifier │                 │    Deterministic Risk Gate  │
   │   (all-MiniLM-L6-v2)        │                 │  (Keywords, Frustration,    │
   │ 10 Intent Centroid Sim.     │                 │   Credentials, Financial)   │
   └──────────────┬──────────────┘                 └──────────────┬──────────────┘
                  │ Intent & Confidence                           │ Risk Level & Flags
                  └───────────────────────┬───────────────────────┘
                                          │
                                          ▼
                         ┌─────────────────────────────────┐
                         │  FAISS Dense Vector Retrieval   │
                         │  (Top-15 Historical Candidates) │
                         └────────────────┬────────────────┘
                                          │
                                          ▼
                         ┌─────────────────────────────────┐
                         │ Hybrid Relevance & Reranking    │
                         │ (Semantic Sim + Lexical Overlap)│
                         └────────────────┬────────────────┘
                                          │
                                          ▼
                         ┌─────────────────────────────────┐
                         │    Operational Routing Engine   │
                         │    (AUTO-HANDLE vs ESCALATE)    │
                         └────────────────┬────────────────┘
                                          │
                                          ▼
                         ┌─────────────────────────────────┐
                         │   Grounded Reply Generation     │
                         │  (Historical Precedent Fused,   │
                         │   Strictly <= 280 Characters)   │
                         └────────────────┬────────────────┘
                                          │
                                          ▼
                            [ Structured Agent Response ]
```

---

## ⏱️ Reproduction Guide (Under 15 Minutes)

The entire repository is self-contained, CPU-optimized, and reproducible offline in **< 15 minutes**.

### 1. Prerequisites & Environment Setup (2 mins)
```bash
# Clone or navigate to the repository
cd new-twitter-pro

# Create and activate virtual environment (Python 3.10 - 3.12)
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies (CPU-optimized)
pip install -r requirements.txt
```

### 2. Run Automated Test Suite (1 min)
Run all 34 automated unit and integration tests:
```bash
python -m pytest tests/
```
*Expected output: `34 passed in ~50s`.*

### 3. Run End-to-End Evaluation Benchmark (1 min)
Execute the complete evaluation suite across all 200 Golden Set holdout cases:
```bash
python scripts/evaluate.py
```
This single command:
- Evaluates the 200 Golden Set holdout cases end-to-end.
- Computes Macro F1, Per-intent breakdown, and saves `results/confusion_matrix.png`.
- Measures retrieval Hit@1, Hit@3, Hit@5, and MRR.
- Evaluates escalation safety (Auto Precision, False Auto Rate, Dangerous Auto Count).
- Executes LLM-as-a-judge rubric scoring and human calibration agreement.
- Categorizes all failures into `results/failure_examples.json`.
- Outputs summary JSONs into `results/metrics.json`.

### 4. Launch Interactive Streamlit Web Application (30 secs)
Launch the interactive support console and failure inspector:
```bash
streamlit run app/streamlit_app.py
```
Open `http://localhost:8501` to test:
- **Live Support Console:** Interactive tweet test box with realistic presets (battery drain, locked Apple ID, billing charge) showing the live decision badge, intent confidence, risk flags, retrieved historical precedents, and generated reply.
- **Evaluation & Benchmarks:** Headline KPIs, confusion matrix heatmap, and baseline comparison table.
- **Failure Mode Inspector:** Drill-down into the top 5 empirical failure modes with concrete real examples from evaluation.

---

## 📁 Repository Structure

```
new-twitter-pro/
├── app/
│   └── streamlit_app.py           # Interactive Support Console & Failure Inspector
├── configs/
│   ├── intents.yaml               # 10 empirical intents, keywords, and exemplars
│   ├── brand_style.yaml           # Apple tone guidelines, constraints (<=280 chars)
│   └── thresholds.yaml            # Operational gating and similarity thresholds
├── data/
│   ├── raw/
│   │   └── twcs.parquet           # Authentic Kaggle dataset (2.8M rows snappy parquet)
│   ├── processed/
│   │   ├── knowledge_base.jsonl   # 63,173 pre-split training threads
│   │   ├── holdout_pool.jsonl     # 15,794 post-split holdout threads
│   │   ├── faiss_index.bin        # Serialized FAISS IndexFlatIP (5,000 cases)
│   │   └── faiss_metadata.json    # Case text and resolution metadata
│   ├── sample/
│   │   └── knowledge_base_sample.jsonl # 5,000 sampled cases for fast local indexing
│   └── golden/
│       ├── golden_set.jsonl       # 200 hand-labelled benchmark cases (20 per intent)
│       └── README.md              # Curation methodology & ambiguity guidelines
├── results/
│   ├── metrics.json               # Consolidated evaluation benchmark KPIs
│   ├── classification_report.json # Per-intent precision, recall, and F1
│   ├── confusion_matrix.png       # High-res 10x10 confusion matrix heatmap
│   ├── escalation_metrics.json    # Auto-handling precision & safety metrics
│   ├── judge_agreement.json       # Human vs LLM judge calibration study
│   ├── failure_examples.json      # Top 5 real failure modes & mitigations
│   ├── reply_scores.json          # Rubric breakdown across 200 cases
│   └── classifier_baselines_comparison.json # Majority vs TF-IDF vs Main
├── scripts/
│   ├── audit_dataset.py           # Kaggle data profiling (108 brands)
│   ├── analyze_brands.py          # Brand comparison audit
│   ├── prepare_data.py            # Clean, reconstruct, and temporal split
│   ├── discover_intents.py        # K-means semantic clustering for taxonomy
│   ├── build_golden_set.py        # Curates the 200 Golden Set benchmark cases
│   ├── build_index.py             # Builds FAISS vector index from cases
│   ├── evaluate_baselines.py      # Benchmarks Majority & TF-IDF vs Main
│   └── evaluate.py                # Master 1-command evaluation runner
├── src/
│   ├── common/                    # Schemas, paths, and LLM fallback clients
│   ├── data/                      # Cleaning, reconstruction, temporal splitting
│   ├── taxonomy/                  # Intent taxonomy loader and validator
│   ├── classifier/                # Baselines (Majority, TF-IDF) & Semantic Centroid
│   ├── retrieval/                 # FAISS Index, Retriever, Hybrid Reranker, Evidence Validator
│   ├── routing/                   # Risk Layer, Escalation Gates, Operational Router
│   ├── generation/                # Prompt templates & grounded Twitter generator
│   ├── evaluation/                # Escalation metrics, Judge, Calibration, Failure analysis
│   └── agent.py                   # Master SupportAgent pipeline orchestration
├── tests/                         # 34 automated pytest tests across all modules
├── BRAND_SELECTION.md             # In-depth brand selection audit report
├── DECISION_LOG.md                # 14 non-obvious architectural decisions
├── REPORT.md                      # Comprehensive 6-page final evaluation report
├── requirements.txt               # Pinned dependencies (CPU-optimized)
└── README.md                      # Project documentation
```

---

## 🛡️ Safety & Escalation Philosophy

In enterprise customer support, **an automated hallucination is 100x worse than a polite deflection**.
- If an automated bot incorrectly tells a customer their subscription has been canceled or provides an incorrect battery disposal recommendation, the company incurs regulatory, financial, and brand liability.
- By contrast, if an inquiry is escalated to a human agent, the customer simply enters standard support triage.

Our routing engine enforces a **zero-tolerance false-automation gate**:
1. **Zero Credential Automation:** Inquiries about Apple ID password resets, two-factor auth lockouts, or activation locks are **never** auto-handled.
2. **Zero Financial Automation:** Billing disputes and credit card charges are **never** auto-handled.
3. **Hardware Safety Overrides:** Battery swelling or overheating inquiries trigger emergency human escalation.
4. **Confidence Backoffs:** Inquiries with cosine confidence $< 0.50$ are routed to human triage to prevent confident hallucinations.

Result: **0.00% False Auto-Handling Rate** across all 200 benchmark cases.

---

## 🔍 Intellectual Honesty: What Is Misleading About Our Headline Numbers?

*(Excerpted from [`REPORT.md`](file:///c:/Users/srira/Desktop/pro/new-twitter-pro/REPORT.md), Section 7)*

1. **100% Auto-Handling Precision Masks Low Coverage (8.5%):**  
   The agent achieves 100% precision by automating only 17 out of 200 cases. It escalates 91.5% of cases! While this guarantees zero unsafe errors, human support agents still bear 91.5% of incoming ticket volume.
2. **4.70/5.0 Judged Quality Masks Metric Gaming:**  
   The automated LLM judge gave escalated replies high scores (~4.72) because they are polite, safe, and short. However, real human evaluators rate canned deflections lower (2.5 - 3.0) when a customer asked a simple troubleshooting question that could have been resolved in 1 step.
3. **Single-Turn Evaluation Masks Multi-Turn Frustration:**  
   Evaluating only Turn 1 ignores customer exasperation when told to "DM us" instead of receiving an immediate public answer.

---

## 🧪 Verification Checklist

- [x] Authentic Kaggle dataset downloaded & reconstructed (79,154 AppleSupport conversations).
- [x] Temporal holdout split enforced (0% conversation ID or author leakage).
- [x] 10-class empirical intent taxonomy discovered from data.
- [x] 200 hand-labelled Golden Set holdout cases curated with explicit actions and risk.
- [x] Baseline models implemented and benchmarked (Majority Class & TF-IDF Logistic Regression).
- [x] FAISS vector index built over 5,000 cases in $< 30$ seconds on CPU.
- [x] Deterministic risk gating layer with credential, financial, and frustration detection.
- [x] Twitter generator enforcing strict $\le 280$ character constraints.
- [x] Master evaluation script (`scripts/evaluate.py`) running in $< 40$ seconds.
- [x] Confusion matrix heatmap generated (`results/confusion_matrix.png`).
- [x] LLM-as-a-judge rubric and statistical human calibration (Spearman $\rho$, Cohen's $\kappa$).
- [x] Top 5 real failure modes documented with concrete examples from evaluation.
- [x] Interactive Streamlit app with live console and failure inspector (`app/streamlit_app.py`).
- [x] 34 automated unit and integration tests passing (`pytest tests/`).
- [x] Max 6-page comprehensive report (`REPORT.md`) with mandatory intellectual honesty section.
- [x] Decision log (`DECISION_LOG.md`) with 14 non-obvious engineering trade-offs.
- [x] Reproduction under 15 minutes verified on standard CPU environment.
