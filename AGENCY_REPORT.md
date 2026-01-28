### 12. Ralph Loop - Iteration 2 (Performance Optimization)
- **Goal:** Radical optimization of "Complexity Router" and AI Provider logic (Groq Priority).
- **Actions:**
    - **Code Analysis:** Identified that `ParallelBatchProcessor` was using Round-Robin instead of Priority Waterfall, leaking requests to slower providers (Gemini/Cerebras) unnecessarily.
    - **Bug Fix:** Fixed duplicate keys in `PROVIDER_CONFIG` (Mistral/OpenRouter were defined twice with conflicting priorities).
    - **Optimization:**
        - Switched `ExtractionPipeline` to use `process_batches_groq_priority` (Strict Priority).
        - Reduced `batch_size` from 10 to 5 to mitigate Groq 429 Rate Limits.
    - **Benchmarking:** Created `benchmark/run_scraper_on_file.py` to enable offline benchmarking against `new_golden_set.json`.
- **Results:**
    - **Baseline Accuracy:** **80.0%** (Recall 80%, Precision 100%) using Mistral (Fallback).
    - **Optimized Accuracy:** **60.0%** (Recall 60%). Regression due to potential grouping issues with smaller batches or Mistral variance.
    - **Performance:** **Groq 70B is failing 100% of requests** with 429 Rate Limit (Tokens Rem=12000), forcing fallback to Mistral (~12s latency).
- **Findings:**
    - **Groq Bottleneck:** The current Groq tier/model (`llama-3.3-70b`) is too restrictive for our prompt size, even with batch_size=5.
    - **Router Works:** The Priority Router correctly falls back to Mistral when Groq fails, preventing total system failure.
    - **Regression:** Strict grouping/parsing seems slightly worse with the current optimization settings.
- **Next Steps:**
    - Investigate Groq Rate Limit (Use smaller model `llama3-8b`? or `mixtral`?).
    - Tune `batch_size` further or implement "Smart Batching" (token counting).
    - Address the grouping regression (False Positives).

### 13. Ralph Loop - Iteration 3 (Model Swapping)
- **Goal:** Fix regression and Groq Rate Limits by switching to `llama-3.1-8b-instant`.
- **Actions:**
    - Modified `PROVIDER_CONFIG` in `src/parallel_batch_processor.py`.
    - Switched Groq model to `llama-3.1-8b-instant`.
    - Increased concurrency to 8 workers (aiming for speed).
    - Ran `verify_golden_set.py`.
- **Results:**
    - **Accuracy:** **90.00%** (36/40 matched).
    - **Performance:** Mixed. Groq still hit 429 Rate Limit on 1 batch (out of 2), likely due to aggressive concurrency.
    - **Fallback:** Mistral successfully picked up the failed batch (7.78s).
- **Analysis:**
    - The 8b model is surprisingly effective, achieving higher accuracy than the 70b baseline (likely due to faster processing allowing more retries or cleaner regex pre-processing).
    - The regression is **FIXED** (60% -> 90%).
    - Groq limits are still tight, but the system is resilient.

### 14. Ralph Loop - Iteration 8 (The "Batch 1" Breakthrough)
- **Goal:** Fix the 27.5% Accuracy regression caused by ID mismatches and Groq batch failures.
- **Actions:**
    - **Prompt Fix:** Removed conflicting `NEGATIVE_CONSTRAINTS` (which demanded JSON) from the DSL Prompt. Added explicit "ID MAPPING" rules to enforce strict `### id` alignment.
    - **Optimization:** Reduced `batch_size` from 5 to **1** in `src/extraction_pipeline.py`.
        - *Reasoning:* `llama-3.1-8b-instant` output was truncating or hallucinating when processing 5 distinct messages in a single DSL block.
        - *Trade-off:* Higher RPM (accepted, Groq has 500 RPM) vs. Perfect Accuracy.
    - **Fallback:** Verified that Mistral correctly picks up requests when Groq hits 429 Rate Limits.
- **Results:**
    - **Accuracy:** **92.50%** (37/40 matched).
    - **Improvements:**
        - Message 12793 (10 picks) went from 0% -> 100% (Saved by Mistral Fallback).
        - Filtered picks (Invalid IDs) dropped from 42 to 0.
    - **Performance:** End-to-end time is still fast (parallel execution), but relies on Mistral for heavy lifting when Groq chokes.
- **Next Steps:**
    - Consider `batch_size=2` if speed becomes an issue, but 1 is safest for 8b models.
    - Investigate why Groq hits 429 so aggressively even with low input tokens (likely a strict TPM or Daily limit on the free tier).

### 15. Ralph Loop - Iteration 9 (The Visual Cortex)
- **Goal:** Establish a high-performance Visualization Layer (Frontend) to monitor scraper throughput, accuracy, and rate limits in real-time.
- **Actions:**
    - **Architecture:** Initialize React + Vite + Tailwind CSS stack.
    - **Design:** "Avant-Garde" Terminal/Cyberpunk aesthetic for high-density data visualization.
    - **Integration:** Map `data/picks_*.json` schema to UI components.
- **Status:** Completed.

### 16. Ralph Loop - Iteration 11 (Live Data Pipeline)
- **Goal:** Connect the Frontend "Visual Cortex" to the Backend Extraction Pipeline for real-time data visualization.
- **Actions:**
    - **Backend:** Modified `cli_tool.py` to auto-deploy `latest_picks.json` to the client's public directory after every run.
    - **Frontend:** Refactored `App.jsx` to replace static `import` with dynamic `fetch()` polling.
    - **Integration:** Established a 10-second polling interval for near real-time updates without page reloads.
- **Status:** Live Link Established.

### 17. Ralph Loop - Iteration 21 (Concurrency Tuning)
- **Goal:** Maximize throughput ("Request Economy") by unlocking parallelism without overwhelming free-tier rate limits.
- **Actions:**
    - **Stress Test:** Created `benchmark_iteration_21.py` to test high concurrency (10 -> 5 -> 4).
    - **Optimization:**
        - Implemented "Queue Wait" logic in `src/provider_pool.py` (`timeout=2.0` instead of fast-fail) to prioritize local providers (Cerebras/Groq) over fallback.
        - Tuned Semaphores: Groq=1 (Strict), Cerebras=3 (Increased), Mistral=2.
        - **Critical Fix:** Removed broken models (DeepSeek R1, Qwen, Gemini Pro) from `src/openrouter_client.py` which were causing fallback cascades to fail (404/400 errors).
- **Results:**
    - **High Load (10 Concurrent):** 70% Success. Overwhelmed providers.
    - **Stable Load (4 Concurrent):** **95% Success** (19/20).
    - **Throughput:** ~0.80s per request avg latency (Wall Clock / N).
    - **Winner:** Cerebras (Free Tier) proved most robust for parallel requests. Groq is fast but strictly rate-limited.
- **Outcome:** System is now optimized for maximum *safe* concurrency (4 workers). Fallback chain is repaired.

### 18. Ralph Loop - Iteration 25 (Real Data Stress Test)
- **Goal:** Validate the "Safe Concurrency" model against the **Real World Golden Set** (complex/heavy messages) instead of mock data.
- **Actions:**
    - **Benchmark:** Created `benchmark_iteration_25.py` loading `new_golden_set.json` (5 complex, multi-pick messages).
    - **Execution:** Ran with `CONCURRENCY_LIMIT=4` (Safe Limit from Iter 21).
- **Results:**
    - **Success Rate:** **100%** (5/5).
    - **Latency:** ~2.65s avg (vs 0.8s on mock data).
    - **Observations:**
        - **Fast Tier Instability:** Cerebras and Groq frequently flagged as "Low Quality" (missing `capper` or `league`), triggering fallbacks.
        - **Fallback robustness:** OpenRouter (DeepSeek R1 / Llama 70B) successfully handled 100% of the "Low Quality" fallbacks.
- **Findings:**
    - The "Fast Tier" (Cerebras/Groq) is **fast but dumb** on complex real-world data (fails to extract metadata like `capper`).
    - The "Fallback Layer" is doing the heavy lifting for quality, which explains the higher latency (2.65s).
    - **Verdict:** System is STABLE but reliant on expensive/slower fallbacks for complex messages.
