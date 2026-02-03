# PRD: Accuracy Optimization Loop (Target 95%)

## Context
The current extraction pipeline achieves ~92.65% accuracy. Recent diagnostic runs show that accuracy can fluctuate (88%-92%) due to unstable AI refinement and edge-case formatting (Unicode, Player Props without colons). We need to hit 95% (65/68) reliably while maintaining performance.

## Requirements
- **Accuracy:** Final benchmark score >= 95% on the `@benchmark_golden_set.py` dataset.
- **Latency:** Total processing time < 45s.
- **Efficiency:** AI call count <= 30 calls.
- **Robustness:** Handle Unicode characters (St Mary's) and non-standard prop formats.

## User Stories

### US-001: Robust Text Normalization
**As a developer**, I want to ensure all source text is normalized to ASCII before processing, **so that** characters like smart quotes or accented letters don't break regex patterns.
- **Acceptance Criteria:**
    - `v0.0.15/src/utils.py` or `rule_based_extractor.py` handles "St Mary’s" correctly.
    - All non-standard dashes and quotes are replaced with standard ASCII equivalents.

### US-002: Advanced Prop Regex
**As a developer**, I want to expand the `RuleBasedExtractor` to catch player props that lack a colon (e.g., "Zion Williamson Over 22.5 Points"), **so that** these are correctly categorized as Player Props instead of Totals.
- **Acceptance Criteria:**
    - `src/rule_based_extractor.py` correctly identifies "Name + Over/Under + Line + Stat" patterns.
    - Diagnostic: Zion Williamson picks are no longer dropped for "No valid team name".

### US-003: Refinement Loop Protection
**As a developer**, I want to prevent the AI refinement loop from overwriting high-confidence (9.0+) rule-based picks with lower-confidence AI results, **so that** we don't regress on accuracy during the "Auditor" phase.
- **Acceptance Criteria:**
    - `src/extraction_pipeline.py` logic preserves high-confidence picks during replacement.
    - Accuracy no longer drops below 92.6% during refinement.

### US-004: Regression Verification
**As a developer**, I want to run the final benchmark and verify all metrics, **so that** I can confirm the 95% target is met.
- **Acceptance Criteria:**
    - `benchmark_golden_set.py` reports >= 95% accuracy.
    - Total processing time is documented.

## Technical Notes
- Target Files: `src/rule_based_extractor.py`, `src/extraction_pipeline.py`, `src/semantic_validator.py`.
- Model Override: Use `google/antigravity-gemini-3-flash` for the TUI agent.
- Run Command: `/c/Users/diego/AppData/Local/Programs/Python/Python311/python.exe benchmark_golden_set.py`.
