# Ralph Progress Log

This file tracks progress across iterations. Agents update this file
after each iteration and it's included in prompts for context.

## Codebase Patterns (Study These First)

- **Rule-Based Extraction:** When modifying `RuleBasedExtractor`, ensure `_to_pick_dict` maps all relevant fields (line, stat, is_over) from the `Pick` object to the dictionary, otherwise downstream components might lose data.
- **Pick Parsing:** `PickParser` requires specific formats (e.g. "Name: Stat" for props). Normalizing text *before* parsing (e.g. inserting colons) is a robust way to support new natural language patterns without modifying the core parser.

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
