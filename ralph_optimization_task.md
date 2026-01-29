# Ralph Optimization Task: Platform Grader Improvement

## Objective
Optimize the Sports Betting Telegram Scraper for **Accuracy**, **Speed**, and **Efficiency** using the `benchmark/run_platform_grader.py` tool.

## Context
The project extracts betting picks from telegram messages. The current implementation faces challenges with:
- **Speed:** Latency per message is too high.
- **Reliability:** API timeouts (Groq/Cerebras) and Rate Limits (429s).
- **Efficiency:** Excessive token usage or redundant API calls.

## Instructions

### 1. Establish Baseline
Run the platform grader to get initial metrics:
```bash
python -m benchmark.run_platform_grader
```
*Note: Default runs on a 50-item subset. Use `export FULL_BENCHMARK=1` for the full dataset.*

### 2. Optimization Loop (The "Ralpheloop")
Iteratively improve the codebase (`src/`) to maximize the score. 

**Priorities:**
1.  **Accuracy (F1 Score):** Must remain > 90% (Target: > 95%).
2.  **Reliability:** 0 crashes/timeouts on the full dataset.
3.  **Speed:** Throughput > 5 messages/sec.
4.  **Efficiency:** Minimize `Tokens/Pick` and `Prompts/Message`.

### 3. Key Areas to Target
- **`src/parallel_batch_processor.py`**: Improve concurrency handling, backoff strategies, and provider fallback logic to prevent timeouts.
- **`src/extraction_pipeline.py`**: Optimize prompt token usage (compress context) and reduce multi-step calls where possible.
- **`src/rule_based_extractor.py`**: Increase regex coverage to bypass AI for simple formats (Speed/Efficiency win).

### 4. Validation
After every significant change, run the benchmark:
```bash
python -m benchmark.run_platform_grader
```
Ensure no regressions in Accuracy while improving Speed/Efficiency.

## Final Goal
Achieve a "Production Ready" grade:
- F1 > 95%
- Throughput > 10 msg/sec
- Cost/Efficiency: < 1000 tokens/pick
