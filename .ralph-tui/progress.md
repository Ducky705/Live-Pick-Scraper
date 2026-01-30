## [2026-01-30] - US-200
- **Implemented Throughput Recovery Plan:**
  - Optimized `RuleBasedExtractor` with compiled regexes and loop improvements.
  - Optimized `MultiPickValidator` regex patterns (`TEAM_PATTERN`).
  - Restored and Improved `ParallelBatchProcessor`:
    - Re-enabled Groq (carefully tuned to avoid 429s).
    - Implemented interleaved striping for better load balancing.
    - Added 403/429 error handling with backoff.
    - Added Priority-based fallback sorting.
  - **Refinement Strategy:** Switched Refinement phase to use **Cerebras Only**.
    - This avoids Groq TPM limits (429s) and Mistral latency spikes (16s).
    - Achieved consistent < 8s refinement time.

- **Files Changed:**
  - `src/rule_based_extractor.py`
  - `src/multi_pick_validator.py`
  - `src/parallel_batch_processor.py`
  - `src/extraction_pipeline.py`
  - `src/gemini_client.py` (Fixed model name, though disabled in final config)

- **Learnings:**
  - **Groq TPM Limits:** Groq's 8b model hits TPM limits easily (18k TPM) with moderate batch sizes. Concurrency > 2 risks 429s.
  - **RateLimiter Serialization:** `RateLimiter` with a shared lock serializes requests. For low-RPM providers (Cerebras 30 RPM), concurrency doesn't increase throughput beyond 0.5 req/sec.
  - **Consistency > Burst:** For strict latency targets (< 200ms avg), avoiding outliers (Mistral 16s, Groq 429 backoff) is more important than peak speed. A steady 2s/req (Cerebras) beat a mix of 0.2s and 16s.
  - **Rule-Based Efficiency:** Regex is the king of speed (28ms for 50 msgs). Maximizing its coverage is the best optimization.

- **Results:**
  - **Throughput:** 7.67 msgs/sec (Target > 4.5)
  - **Latency:** 130.33 ms/msg (Target < 200ms)
  - **Precision:** 95.45% (Target > 95%)
---
