# Ralph Progress Log

This file tracks progress across iterations. Agents update this file
after each iteration and it's included in prompts for context.

## Codebase Patterns (Study These First)

*   **Adaptive Batching:** `AdaptiveConcurrencyLimiter` in `parallel_batch_processor.py` is crucial for handling flaky APIs (Groq/Cerebras).
*   **Validator-Driven AI:** `RuleBasedExtractor` is fast but brittle. `MultiPickValidator` forces AI fallback when simple signals (Team Names) are missed.
*   **Hybrid Throughput:** Combining fast/limited providers (Groq) with high-capacity/slow providers (Mistral) via `process_batches` yields best results.

---

## 2026-01-29 - US-005
- **Implemented:** Deep Optimization Loop for Recall and Throughput.
- **Files Changed:**
    - `src/rule_based_extractor.py`: Added regex normalizations (U162->Under 162, MI->ML) to fix common parse errors.
    - `src/multi_pick_validator.py`: Added "Uncovered Team" detection to force AI re-parse when team names appear in text but not in picks.
    - `src/parallel_batch_processor.py`: Optimized provider config (Groq: 2 concurrent, Cerebras: 1 concurrent, Mistral: 20 concurrent). Redirected `groq_priority` to use ALL providers in parallel.
    - `src/extraction_pipeline.py`: Increased default `batch_size` to 10.
- **Learnings:**
    - **Gotcha:** `RuleBasedExtractor` handles ~90% of messages but misses complex ones. Without strict validation (counting Team Names), these misses are silent.
    - **Gotcha:** High concurrency on Rate-Limited APIs (Groq/Cerebras) causes 429 loops that are slower than just using a slower provider (Mistral) correctly.
    - **Pattern:** Using `batch_size=10` doubles effective throughput for RPM-limited providers.
