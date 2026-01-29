# Ralph Wiggum Task: Verify Reliability & Execute Stress Test

You are an expert Backend Engineer. The previous "Mega-Scale Stress Test" attempt failed or was interrupted. Your goal is to fix the reliability mechanisms and successfully complete the 500-message benchmark without degrading existing performance.

## 🛡️ PRIME DIRECTIVES (DO NOT IGNORE)
1.  **PRESERVE CORE LOGIC:** Do NOT modify the logic inside `src/extraction_pipeline.py` or the prompt templates in `src/prompts/` unless absolutely necessary to prevent a crash. The current accuracy (100%) and latency (~0.6s) must be maintained.
2.  **ADDITIVE CHANGES ONLY:** Implement reliability features (retries, backoff, circuit breakers) as *wrappers* or *extensions* to the existing client, not by rewriting the core extraction flow.
3.  **REGRESSION CHECK:** Before running the massive stress test, run the small "Golden Set" (`verify_golden_set.py`) to ensure basic functionality is still perfect.

## PHASE 1: CODE AUDIT & REPAIR (CRITICAL)
1.  **Inspect `src/groq_client.py` and `src/parallel_batch_processor.py`**:
    *   Verify **Adaptive Concurrency** logic exists (does it reduce concurrency on 429/500 errors?).
    *   Verify **Latency Budget** logic exists (is there a timeout/abort mechanism?).
    *   *If code is missing or broken, IMPLEMENT IT NOW.*

2.  **Verify via Tests**:
    *   Run `python verify_golden_set.py` FIRST. If this fails, STOP and fix the regression.
    *   Create or run `tests/test_adaptive_concurrency.py`.
    *   Create or run `tests/test_latency_enforcement.py`.

## PHASE 2: GENERATE DATASET
1.  Check if `benchmark/dataset/stress_test_500.json` exists and is valid.
2.  If not, generate it:
    *   500 messages total.
    *   Mix: 60% Simple (One-line bets), 30% Moderate (Parlays), 10% Complex (Esports/Nested).

## PHASE 3: EXECUTE STRESS TEST
1.  Run the pipeline against `benchmark/dataset/stress_test_500.json`.
    *   Command: `python benchmark/stress_test.py` (create if needed).
    *   Settings: `BATCH_SIZE = 1`, Initial `CONCURRENCY = 10`.
2.  **Monitor & Log**:
    *   Track successful extractions vs. failures.
    *   Track latency per request (P50, P90, P99).
    *   Track rate limit hits (should be handled by adaptive concurrency, not crash).

## PHASE 4: FINAL REPORT
*   Update `benchmark/results/stress_test_report.md` with the run statistics.
*   If the test passes with >99% success and stable latency, we are ready for Frontend integration.

## COMPLETION INSTRUCTION
When you have successfully completed all phases and the stress test passes as defined in Phase 4, you MUST output the following string on a new line:
STRESS_TEST_COMPLETE
