# Ralph Progress Log

This file tracks progress across iterations. Agents update this file
after each iteration and it's included in prompts for context.

## Codebase Patterns (Study These First)

- **Early Normalization**: Always normalize source text (including OCR) to ASCII early in the processing pipeline (e.g., in `ExtractionPipeline.run`) to ensure consistency across rule-based and AI-based extraction routes. Use `src.utils.normalize_to_ascii`.

---

## 2026-02-03 - US-001
- Implemented robust ASCII normalization utility `normalize_to_ascii` in `src/utils.py`.
- Integrated `normalize_to_ascii` early in `ExtractionPipeline.run` to handle both text and OCR content.
- Standardized normalization in `RuleBasedExtractor.py` using the new utility.
- Added `st.` and `st` aliases for Saint Mary's and other "Saint" teams in `src/team_aliases.py` to ensure correct validation.
- Files changed: `src/utils.py`, `src/extraction_pipeline.py`, `src/rule_based_extractor.py`, `src/team_aliases.py`.
- **Learnings:**
  - Standardizing normalization early prevents downstream parsing issues with smart quotes and Unicode dashes.
  - Adding common variations (like `st.` for `saint`) to team aliases is crucial for the semantic validator.
---

