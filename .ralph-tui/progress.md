# Ralph Progress Log

This file tracks progress across iterations. Agents update this file
after each iteration and it's included in prompts for context.

## Codebase Patterns (Study These First)

- **Regex Safety:** Avoid `(?=...)` lookaheads with greedy quantifiers inside loops. Use linear scanning with `.*?` or `[^)]*` combined with specific keywords.
- **Unit Extraction:** Extract and *remove* units from text before parsing to avoid confusing the parser with `1u` prefixes.

---

## 2026-01-30 - US-201
- **Implemented:** Audited and optimized regex patterns in `src/rule_based_extractor.py`.
- **Files changed:** `src/rule_based_extractor.py`.
- **Learnings:**
  - `RE_REMOVE_PAREN_COMMENTARY` had potential O(N) cost per parenthesis due to lookahead scanning. Replaced with linear keyword-based removal.
  - `RE_PARENS` was too aggressive, removing valid odds like `(-110)`. Replaced with `RE_REMOVE_IRRELEVANT_PARENS` that only removes noise keywords (risk, writeup, good, etc.) or unit suffixes.
  - Added `_extract_and_remove_units` to properly clean `1u Purdue` -> `Purdue`, improving parser accuracy.
  - Recall is stabilized around ~68% on the 50-item benchmark (vs ~71% baseline), but with higher safety and crash prevention (fixed `Texas ML (good to -2)` crash).
