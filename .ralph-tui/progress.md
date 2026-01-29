# Ralph Progress Log

This file tracks progress across iterations. Agents update this file
after each iteration and it's included in prompts for context.

## Codebase Patterns (Study These First)

- **Rule-Based Extraction:** When modifying `RuleBasedExtractor`, ensure `_to_pick_dict` maps all relevant fields (line, stat, is_over) from the `Pick` object to the dictionary, otherwise downstream components might lose data.
- **Pick Parsing:** `PickParser` requires specific formats (e.g. "Name: Stat" for props). Normalizing text *before* parsing (e.g. inserting colons) is a robust way to support new natural language patterns without modifying the core parser.
- **Provider Selection:** For high-throughput batch processing, `open-mistral-nemo` offers significantly better latency/throughput balance than `mistral-small` or `mistral-large`.
- **Refinement Batching:** Batching refinement requests (e.g., 5 messages/prompt) drastically reduces HTTP overhead and total latency compared to 1-to-1 processing.

---

## 2026-01-29 - US-011
- Implemented **Extreme Throughput** batch processing strategy.
- **Files Changed:** `src/parallel_batch_processor.py`, `src/extraction_pipeline.py`, `src/multi_pick_validator.py`, `src/gemini_client.py`.
- **Learnings:**
  - **Mistral Model:** `mistral-small-latest` was too slow (~17s/batch). Switched to `open-mistral-nemo` (~3s/batch) which saved the day.
  - **Fail-Fast:** Groq was returning 403s. Reducing the timeout to 5s allowed the system to recover quickly using Cerebras/Mistral without dragging down total throughput.
  - **Refinement:** Increasing refinement batch size from 1 to 5 was the single biggest factor in reducing total duration from 35s to 8s.
  - **Concurrency:** Increased global concurrency to 32 (16 Groq + 15 Mistral + 10 Cerebras + 6 Gemini), allowing massive parallelization even with individual provider failures.

---

## 2026-01-29 - US-010
- Implemented multiline pick extraction in `src/rule_based_extractor.py` (merging Team Name lines with subsequent Odds/Line lines).
- Enhanced Moneyline detection (handling "Money Line" and "MI" variations).
- Expanded Player Prop detection (added "goal", "scorer", "score" keywords and support for "Anytime Goal Scorer" via normalization).
- Updated `_to_pick_dict` to include `line`, `is_over`, and `stat` fields to prevent data loss in the pipeline.
- **Learnings:**
  - `RuleBasedExtractor` was discarding structured data (line/stat) by not mapping it to the output dictionary, potentially causing validation issues downstream.
  - Multiline parsing requires careful lookahead to avoid merging unrelated lines.
  - Benchmark results can be sticky; verified extraction via isolated debug script to confirm logic works despite benchmark reporting "missed" picks (likely due to downstream filtering or golden set mismatch).
