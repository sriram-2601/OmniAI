# Architectural Decision Log: @AppleSupport AI Agent

This document records **14 non-obvious engineering decisions** made during the design, implementation, and benchmarking of the `@AppleSupport` AI customer support agent. Each entry documents the context, the decision taken, the alternatives considered, the explicit trade-offs evaluated, and the empirical impact on the system.

---

### Decision 1: Brand Selection — Choosing `@AppleSupport` over `@AmazonHelp` and `@Uber_Support`
- **Context & Problem:** The Kaggle dataset contains 108 brands. Building an effective agent requires a brand with sufficient volume, high data cleanliness, verifiable resolution evidence, and non-trivial domain complexity.
- **Decision:** Selected `@AppleSupport` (106,860 brand replies, 75.4% URL grounding).
- **Alternatives Considered:**
  1. `@AmazonHelp`: Highest volume (166k replies), but fragmented across dozens of languages (Spanish, German, Japanese, Portuguese) and regional policies.
  2. `@Uber_Support`: High volume (49k replies), but 90%+ of cases involve immediate PII or private trip dispute refunding with minimal public troubleshooting.
  3. `@SpotifyCares`: Good English consistency, but narrow domain almost exclusively focused on playback streaming bugs and billing.
- **Rejection Rationale:** `@AmazonHelp` would have required multilingual embedding pipelines and multi-region routing models, diluting focus on core reasoning and safety. `@Uber_Support` had poor grounding (<19% URLs) and consisted mostly of automated form deflection.
- **Empirical Impact:** `@AppleSupport` provided 99%+ English consistency, clear technical problem boundaries, and an authoritative set of support URLs (`support.apple.com`), making grounding verifiable.

---

### Decision 2: Temporal Split instead of Random Train/Test Split
- **Context & Problem:** Evaluating conversational support agents using standard random k-fold or random train/test splits risks severe data leakage.
- **Decision:** Enforced a strict temporal cutoff: Precedents / KB from **March 2016 to November 16, 2017** (63,173 threads); Evaluation Holdout Pool from **November 16, 2017 to December 3, 2017** (15,794 threads).
- **Alternatives Considered:**
  1. Random 80/20 train/test split.
  2. Stratified split grouped by conversation ID.
- **Rejection Rationale:** Random split causes future data leakage (predicting 2016 issues using 2017 solutions) and conversation leakage (Turn 1 in train, Turn 2 in test). Even conversation-grouped random split leaks global temporal events (e.g. the November 2017 iOS 11.1.1 release date).
- **Empirical Impact:** Completely authentic generalization testing. 0% conversation ID overlap and 0% customer author ID overlap. Evaluated on the real-world iOS 11 launch spike.

---

### Decision 3: 10-Class Empirically Discovered Taxonomy instead of Ad-Hoc Categories
- **Context & Problem:** Machine learning classifiers fail when taxonomies are arbitrarily invented without grounding in real conversation distribution.
- **Decision:** Ran k-means semantic clustering and TF-IDF n-gram extraction over 15,000 historical customer inquiries to derive 10 empirical clusters (`configs/intents.yaml`).
- **Alternatives Considered:**
  1. High-level 3-class taxonomy (`HARDWARE`, `SOFTWARE`, `BILLING`).
  2. Fine-grained 50-class taxonomy (e.g., `IPHONE_X_FACEID`, `AIRPODS_LEFT_EAR_DISCONNECT`).
- **Rejection Rationale:** 3 classes is too coarse for actionable routing (software update vs battery drain require radically different actions). 50 classes leads to high class confusion and data sparsity under social tweet brevity.
- **Empirical Impact:** Balanced coverage: 10 intents capture 97.8% of historical inquiry volume, achieving 64.59% Macro F1 and 85.7% F1 on sensitive credential inquiries.

---

### Decision 4: CPU-Optimized Dense Semantic Centroid Classifier (`all-MiniLM-L6-v2`)
- **Context & Problem:** The support agent must run offline, reproducibly, and efficiently on standard CPU developer machines without requiring dedicated GPU cloud clusters.
- **Decision:** Implemented a dense semantic centroid classifier utilizing `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional normalized embeddings).
- **Alternatives Considered:**
  1. Fine-tuned BERT / RoBERTa cross-encoder.
  2. Closed-source proprietary LLM zero-shot classification (e.g., GPT-4o-mini).
  3. Pure TF-IDF + Logistic Regression.
- **Rejection Rationale:** Fine-tuning a heavy transformer requires GPU infrastructure and slows inference to >300ms/query. Closed-source LLMs introduce rate limits, network latency, variable costs, and zero offline reproducibility.
- **Empirical Impact:** Single-query inference executes in **8.4 ms** on CPU; Macro F1 reached 64.59% without a single training parameter update, with zero API token costs.

---

### Decision 5: FAISS Vector Indexing with Exact Inner Product (IP) on L2-Normalized Vectors
- **Context & Problem:** The retriever must search thousands of historical precedent cases with low latency and exact cosine similarity ranking.
- **Decision:** Selected `faiss.IndexFlatIP` over unit-normalized embeddings.
- **Alternatives Considered:**
  1. `faiss.IndexIVFFlat` (Inverted File Index with clustering).
  2. `faiss.IndexHNSWFlat` (Hierarchical Navigable Small World graphs).
  3. Scikit-learn `NearestNeighbors` (Brute-force ball tree).
- **Rejection Rationale:** For 5,000 to 50,000 vectors, approximate indices (IVF/HNSW) introduce unnecessary approximation error and index construction overhead without significant speedup. Scikit-learn does not support native SIMD vectorization.
- **Empirical Impact:** Indexing 5,000 support cases took only **28 seconds** on CPU; retrieval queries take **< 4 ms** with 100% exact mathematical cosine similarity.

---

### Decision 6: Hybrid Reranking (Semantic Dense Sim + Lexical Jaccard + Substantiveness)
- **Context & Problem:** Raw semantic vector search often retrieves tweets that are semantically related in topic but functionally useless (e.g. "We'd love to help, please DM us!").
- **Decision:** Built a multi-stage hybrid reranker (`src/retrieval/rerank.py`) combining dense cosine similarity (60% weight), lexical Jaccard overlap (25% weight), and a substantiveness bonus for structured settings paths (`Settings > ...`) and URLs (15% weight).
- **Alternatives Considered:**
  1. Pure dense cosine similarity ranking.
  2. Heavy neural cross-encoder reranker (e.g. `ms-marco-MiniLM-L-6-v2`).
- **Rejection Rationale:** Pure dense search frequently ranks non-actionable canned replies at top-1. Neural cross-encoders add 80-120ms latency per query on CPU.
- **Empirical Impact:** Hit@3 relevance reached **73.0%** and Hit@5 reached **79.0%**, ensuring that retrieved precedents contain actionable diagnostic paths.

---

### Decision 7: Runtime Leakage Prevention via Dynamic `exclude_case_id`
- **Context & Problem:** During benchmark evaluation, if an evaluation inquiry exists in the precedent pool, a nearest-neighbor search will achieve a trivial 1.0 similarity score by retrieving itself.
- **Decision:** Implemented strict candidate over-fetching (`top_k + 2`) and dynamic filtering on `exclude_case_id` during search execution.
- **Alternatives Considered:**
  1. Completely removing all test cases from the index files prior to indexing.
  2. Relying strictly on temporal separation.
- **Rejection Rationale:** Removing test cases from the index beforehand requires maintaining multiple index artifacts on disk. Relying solely on temporal separation does not prevent synthetic duplicate queries.
- **Empirical Impact:** Guaranteed 0.0% evaluation self-retrieval leakage without needing separate database copies.

---

### Decision 8: Zero-Tolerance Credential & Financial Safety Gates
- **Context & Problem:** Automated customer support bots often trigger severe brand disasters by hallucinating policy exceptions, promising unauthorized refunds, or mishandling passwords publicly.
- **Decision:** Engineered hard rule-based safety overrides (`src/routing/risk.py`, `router.py`): any inquiry involving password reset, locked Apple ID, two-factor auth, credit card charges, or refunds is hard-escalated to human review.
- **Alternatives Considered:**
  1. Allowing the LLM to auto-respond to refund inquiries with general policy text.
  2. Soft-weighting financial risk into a continuous confidence probability.
- **Rejection Rationale:** Generative models cannot be trusted with financial liability or authentication security on public Twitter feeds.
- **Empirical Impact:** **0.00% False Auto-Handling Rate** and **0 Dangerous Auto-Handling incidents** across 200 Golden benchmark cases.

---

### Decision 9: Precedent Synthesis Generator with Strict 280-Character Budget
- **Context & Problem:** Twitter enforces a strict 280-character limit. Free-form LLM generation frequently overflows character limits or produces repetitive fluff.
- **Decision:** Implemented a template-and-precedent synthesis engine (`src/generation/generator.py`) with hard truncation, character validation, and deterministic precedent extraction.
- **Alternatives Considered:**
  1. Direct zero-shot LLM generation without length guards.
  2. Post-generation aggressive word-wrapping.
- **Rejection Rationale:** Post-generation truncation cuts off sentences mid-word or deletes URLs. Direct zero-shot generation violates character constraints ~15-20% of the time.
- **Empirical Impact:** 100% of generated draft replies strictly meet the $\le 280$ character constraint (average length: 154 characters), preserving brand tone and direct links.

---

### Decision 10: Curating a Balanced 200-Case Golden Benchmark Set
- **Context & Problem:** Automated testing on noisy unlabelled social data measures noise rather than model fidelity.
- **Decision:** Hand-labelled exactly 200 holdout cases (`data/golden/golden_set.jsonl`), balanced at 20 cases per intent, with explicit `expected_action` (`AUTO_HANDLE` vs `ESCALATE`) and risk annotations.
- **Alternatives Considered:**
  1. Evaluating on 5,000 silver-labelled noisy tweets.
  2. Using an external synthetic benchmark (e.g. Banking77).
- **Rejection Rationale:** Silver-labelled benchmarks have a 20-30% label noise rate that corrupts evaluation. Banking77 represents banking, not hardware/device support.
- **Empirical Impact:** Provided an unshakeable ground truth to benchmark baselines, calculate real confusion matrices, and evaluate safety trade-offs.

---

### Decision 11: Statistical Calibration of LLM-as-a-Judge vs Human Ratings
- **Context & Problem:** Many AI projects report high "LLM Judge" scores (e.g., 4.8/5) without verifying whether the automated judge agrees with human common sense.
- **Decision:** Implemented formal statistical calibration (`src/evaluation/calibration.py`) computing Spearman rank correlation ($\rho$), Pearson linear correlation ($r$), MAE, and Quadratic Weighted Cohen's Kappa ($\kappa$) on 50 sample pairs.
- **Alternatives Considered:**
  1. Reporting the raw 4.70/5.0 judge score without calibration.
  2. Manually rating all 200 cases without automated scaling.
- **Rejection Rationale:** Blindly trusting LLM-as-a-judge introduces circular reasoning.
- **Empirical Impact:** Discovered that the automated judge has a negative correlation ($\rho = -0.3172$) with human ratings because it over-rewards safe deflection ("Please DM us") where humans expect direct first-contact answers. This became the centerpiece of our Intellectual Honesty section.

---

### Decision 12: Empirical Categorization of 5 Concrete Failure Modes
- **Context & Problem:** High-level metrics (e.g. 65% F1) obscure what actually breaks in production.
- **Decision:** Programmed automated error parsing (`src/evaluation/failure_analysis.py`) categorizing every evaluation failure into one of 5 empirical modes with concrete examples and mitigations.
- **Alternatives Considered:**
  1. Writing generic speculative failure descriptions in documentation.
  2. Only reporting a confusion matrix.
- **Rejection Rationale:** Generic failure write-ups lack credibility. Engineers need to see real customer tweets and exact failure triggers.
- **Empirical Impact:** Identified compound multi-intent ambiguity (35 cases) and precedent generalization (86 cases) as the dominant bottlenecks for future roadmap work.

---

### Decision 13: Local Caching of Model Weights and Precomputed Embeddings
- **Context & Problem:** Evaluation suites that depend on real-time downloads from Hugging Face Hub fail under offline conditions, rate-limiting, or intermittent network drops.
- **Decision:** Cached the `all-MiniLM-L6-v2` transformer weights in the local cache and serialized the 5,000 FAISS vector database to `data/processed/faiss_index.bin`.
- **Alternatives Considered:**
  1. Dynamic streaming of vector embeddings over network APIs.
  2. On-the-fly index re-creation during every script execution.
- **Rejection Rationale:** Index re-creation adds 30 seconds to every script run. Dynamic API calls fail when network connectivity drops.
- **Empirical Impact:** The entire evaluation suite runs in **34.6 seconds** completely offline without downloading external assets.

---

### Decision 14: Interactive Streamlit UI with Evidence Traces and Failure Inspector
- **Context & Problem:** Reviewers need to verify agent behavior interactively, test custom edge cases, and inspect why an inquiry was auto-handled or escalated.
- **Decision:** Built a multi-page interactive console (`app/streamlit_app.py`) featuring live inference with presets, benchmark dashboards, confusion matrix viewing, and interactive failure case drill-down.
- **Alternatives Considered:**
  1. Pure CLI script outputs.
  2. Static Jupyter Notebook demo.
- **Rejection Rationale:** CLI tools cannot display rich interactive evidence expanders or confusion matrix heatmaps easily. Jupyter notebooks often suffer from execution order issues and state bugs.
- **Empirical Impact:** Reviewers can test arbitrary customer tweets in real-time, see exact precedent similarity scores, and review failure mitigations in seconds.
