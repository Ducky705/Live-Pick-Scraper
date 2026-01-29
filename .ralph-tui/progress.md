# Ralph Progress Log

This file tracks progress across iterations. Agents update this file
after each iteration and it's included in prompts for context.

## Codebase Patterns (Study These First)

*Add reusable patterns discovered during development here.*

---

## 2026-01-29 - US-001
- **Implemented:**
  - Ran platform grader benchmark to establish baseline.
  - Analyzed performance metrics.
- **Metrics:**
  - F1 Score: 61.30% (Recall: 45.38%, Precision: 94.44%)
  - Throughput: 0.46 msgs/sec
  - Duration: 109s
- **Learnings:**
  - **Bottleneck:** Low Recall (45%) is the primary issue. 142 picks missed.
  - **Performance:** Rate limits (429) on Groq/Cerebras significantly impact throughput during the refinement phase.
  - **Pattern:** Large multi-pick messages (like MSG 2015078297160270275) are a major source of missed picks if the extractor fails to parse the list structure correctly.
  - **Gotcha:** Rule-based extraction is fast (48/50 msgs) but the subsequent refinement step for 18 messages caused rate limit delays.
---
