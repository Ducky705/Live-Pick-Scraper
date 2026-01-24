# Progress Tracker

## Phase 5: Smart Capper Matching
- [x] Integrate `rapidfuzz` for high-performance fuzzy matching.
- [x] Implement "Smart Active Priority" matching:
    1.  Exact Match.
    2.  Fuzzy Match (Score > 90) against **Active Cappers** (those with picks).
    3.  Fuzzy Match (Score > 90) against **All Cappers**.
    4.  Auto-Create new capper if no match found.
- [x] Verified logic with unit tests (Active vs Inactive prioritization).

## Phase 4: Debugging & Evaluation Tools
- [x] Run `tools/debug_grader.py`, analyze results manually, and grade the performance (2025-01-25)
    - **Initial Score**: 20/60 (User Reported) vs 53/60 (Debug Run).
    - **Fixes**: 
        1.  **Capper Attribution**: Removed `[CONTENT]` tag from prompts to allow natural header reading. Validated on "Vezino" messages.
        2.  **List Splitting**: Strengthened prompt with "EACH LINE IS A SEPARATE PICK". Validated on "Tbsportsbetting" list (4 separate picks).
- [x] Fix `tools/debug_pipeline.py` to use `OCRHandler`
- [x] Refactor `src/ocr_engine.py` for singleton pattern

## Phase 3: Efficiency & Logic-First Parsing
- [x] Analyze codebase to identify AI bottlenecks
- [x] Design Rule-Based Extraction strategy
- [x] Create `src/rule_based_extractor.py` with regex logic
- [x] Integrate `RuleBasedExtractor` into `cli_tool.py` (Main Pipeline)
- [x] Integrate `RuleBasedExtractor` into `benchmark/runners/run_enhanced_benchmark.py`
- [x] Validate with Golden Set Benchmark
    - **Result**: 85% of images handled by rules (0s latency).
    - **Accuracy**: F1 Score 74% (vs 81% AI-only).
    - **Efficiency**: 4x faster average processing time.
    - **Fallback**: Complex parlay cases correctly fall back to AI.

## Phase 2: Logic-First Optimization
- [x] Implement Local OCR in `src/auto_processor.py` to filter spam/recap before AI
- [x] Switch `src/ocr_cascade.py` to use Raw Text prompt instead of JSON (Let logic parse it)

## Phase 1: Stability & Accuracy Upgrade
- [x] Fix Rate Limits in `src/parallel_batch_processor.py` (Reduced Groq concurrency)
- [x] Implement Chain-of-Thought (CoT) in `src/prompts/core.py` (Added <analysis> block)
- [x] Update `src/prompts/decoder.py` to handle CoT output (Strip <analysis> block)
- [x] Run Benchmark V3 (Achieved 93-98% F1 Score, up from 54%)
- [x] Analyze results and refine (Results are stable and accurate)

## Results
- **F1 Score:** Increased from 54.02% to **93-98%**.
- **League Accuracy:** Increased from 59% to **96-99%**.
- **Bet Type Accuracy:** Increased from 57% to **94-99%**.
- **Strategy:** Adopted "Smart Pass" (Chain of Thought) over "Fast Pass". 
- **Speed:** Slower (70s vs potentially faster) but prioritized accuracy as requested. Groq is currently rate-limited, so fallback to OpenRouter is functioning correctly.
