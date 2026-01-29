# Ralph Progress Log

This file tracks progress across iterations. Agents update this file
after each iteration and it's included in prompts for context.

## 2026-01-29 - US-006
- Implemented less aggressive `MultiPickValidator` (Confidence > 0.7 required for reparse).
- Increased `ExtractionPipeline` batch size to 20 for higher throughput.
- Verified `ParallelBatchProcessor` timeouts are aligned with larger batches.
- **Files changed:** `src/multi_pick_validator.py`, `src/extraction_pipeline.py`
- **Learnings:**
  - `ExtractionPipeline` controls the effective batch size sent to providers.
  - `MultiPickValidator` was flagging missing picks with low confidence (0.5), leading to unnecessary reparses.
  - Large batches (20) with Groq require careful TPM management, but `AdaptiveConcurrencyLimiter` should handle 429s.
---

