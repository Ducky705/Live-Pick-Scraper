# Ralph Progress Log

This file tracks progress across iterations. Agents update this file
after each iteration and it's included in prompts for context.

## Codebase Patterns (Study These First)

- **Provider Concurrency:** High-TPM/High-Latency providers (like Mistral Large) require high concurrency (20+) to achieve good throughput. Low-latency providers (Groq) are often TPM-limited and need strict throttling (1-2 concurrent).
- **Adaptive Limits:** Global adaptive limits are dangerous in heterogeneous pools. Flaky providers can throttle healthy ones. Use per-provider adaptive limits.

---

## 2026-01-29 - US-002
- **Implemented:**
  - **Per-Provider Adaptive Concurrency:** Replaced global limiter with per-provider limiters to isolate failures.
  - **Exponential Backoff:** Implemented smart backoff for 429s and Timeouts in `_execute_request`.
  - **Parallelized Fallback:** Phase 2 retries now run in parallel using `ThreadPoolExecutor`.
  - **Optimized Configuration:** Increased Mistral (20) and Gemini (10) concurrency; Reduced Groq (1) to prevent 429s.
- **Files Changed:**
  - `src/parallel_batch_processor.py`
  - `tests/test_adaptive_concurrency.py`
- **Learnings:**
  - **Gotcha:** `ThreadPoolExecutor` handles tasks, but `AdaptiveConcurrencyLimiter` throttles execution. If the limiter is global, a failure in one provider blocks threads for all providers.
  - **Pattern:** Mistral Large is very slow (~20s/batch) but has huge TPM. Parallelism is the only way to use it effectively.
  - **Performance:** Achieved 0.81 msgs/sec in partial benchmark (limited by Mistral latency), but zero timeouts and robust recovery from 429s.

---

## 2026-01-29 - US-001
- **Implemented:**
  - Ran platform grader benchmark to establish baseline.
  - Analyzed performance metrics.
- **Metrics:**
  - F1 Score: 61.30% (Recall: 45.38%, Precision: 94.44%)
  - Throughput: 0.46 msgs/sec
  - Duration: 109s
- **Learnings:**
  - **Bottleneck:** Low Recall (45%) is the primary issue. 142 picks missed.
  - **Performance:** Rate limits (429) on Groq/Cerebras significantly impact throughput during the refinement phase.
  - **Pattern:** Large multi-pick messages (like MSG 2015078297160270275) are a major source of missed picks if the extractor fails to parse the list structure correctly.
  - **Gotcha:** Rule-based extraction is fast (48/50 msgs) but the subsequent refinement step for 18 messages caused rate limit delays.
---
