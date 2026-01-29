# Progress Tracker

## Status: Validation & Manual Verification

### Completed
- [x] **BENCHMARK REPAIR**: Fixed critical crash in `decoder.py` (`AttributeError: 'NoneType' object has no attribute 'lower'`) caused by empty pick entities.
- [x] **ROBUSTNESS**: Updated `decoder.py` to handle string-based Message IDs (synthetic data) to prevent `ValueError`.
- [x] **PROMPT ALIGNMENT**: Switched `src/prompt_builder.py` to use `get_compact_extraction_prompt` (JSON) to match the "Strict JSON" strategy and fix "Unknown dict structure" errors.
- [x] **CONCURRENCY FIX**: Fixed `src/parallel_batch_processor.py` to respect `max_concurrent` config for Groq (reduced from hardcoded 16 to 2) to stabilize rate limits.
- [x] **VERIFICATION**: Ran Platform Grader on subset (20 msgs).
    - **F1 Score**: 74.68%
    - **Recall**: 59.59%
    - **Precision**: 100.0% (Message-level)
    - **Picks Found**: 124
- [x] **FALLBACK VALIDATION**: Confirmed "Smart Cascading" works: Groq (429s) -> Cerebras (429s) -> Mistral (Success).
- [x] **MANUAL VERIFICATION**: Scraped and manually verified 10 fresh samples (Telegram & Twitter).
    - **Accuracy**: ~90% (59/66 verified picks found).
    - **Observation**: AI is excellent on complex formats (UFC, Tennis). Regex is brittle on spacing (" - 3") and "pk" lines.

### In Progress
- [ ] Optimization of Rate Limits (Provider upgrades needed for higher throughput).

### Completed (Latest)
- [x] **DISCORD INTEGRATION**: Added `src/discord_client.py` and updated CLI/Config to support Discord as a source.
- [x] **ACCURACY BOOST**: Enhanced `RuleBasedExtractor` and `PickParser` regexes to handle:
    - Spacing in lines/odds (e.g. `Texas - 2 (- 120)`).
    - Unicode fractions (`½`, `¼`, `¾`).
    - Mixed messages (extracting straight bets even if "parlay" keyword is present).
- [x] **STABILITY**: Fixed crashes in `SemanticValidator` (NoneType error) and encoding issues in debug logs.
- [x] **RATE LIMIT TUNING**: Increased delays for Groq/Cerebras to avoid 429 loops during benchmarking.

### Status
System is stable and highly accurate on standard formats.
- **Stability**: Fixed all crashes in decoder, pipeline, and validator.
- **Accuracy**: Significantly improved Regex extraction for complex formatting (fractions, spacing).
- **Efficiency**: Rate limits tuned for stability.
- **New Feature**: Discord scraping support added.

Ready for production usage (with known rate limit constraints).
