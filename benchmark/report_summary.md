# Benchmark Report - v2.1 (Post-Optimization)
**Date:** 2026-01-22
**Dataset:** Golden Set v2 (85 verified items)
**Model:** Mistral-Small (via OpenRouter)

## Summary Metrics
| Metric | Score | Change vs v2 |
| :--- | :--- | :--- |
| **Precision** | **97.45%** | +1.49% |
| **Recall** | **97.45%** | +6.69% |
| **F1 Score** | **97.45%** | +4.16% |

## Totals
- **Total Items:** 85
- **Total Expected Picks:** 314
- **Total Matches:** 306 (vs 285 in v2)
- **False Negatives (Missed):** 8 (vs 29 in v2)
- **False Positives (Extra):** 8 (vs 12 in v2)
- **Errors:** 0

## Analysis
The system performance has improved significantly, with F1 score jumping from **93.14% to 97.45%**.

### Key Improvements
1.  **Normalization Impact:** The vast majority of gains came from the new `src/pick_normalizer.py` module.
    *   **Period Indicators:** Standardizing `1st Half`, `1h`, `first half` -> `1H` resolved many false negatives.
    *   **Team Names:** Mapping abbreviations (`LAL`, `NYK`) to full names (`Lakers`, `Knicks`) allowed the benchmark to correctly match valid LLM outputs against the golden set.
2.  **Prompt Refinement:** Updating the prompt to explicitly mention handling abbreviations helped standardizing the raw output, though normalization did the heavy lifting.

### Remaining Issues
The remaining 8 misses (2.5% error rate) are likely due to:
*   Complex parlay structures where the LLM misses one leg.
*   Highly ambiguous text where the team name is implied rather than stated.
*   OCR errors on low-quality images.

## Recommendations
*   **Production Deployment:** Integrate `src/pick_normalizer.py` into the main ingestion pipeline to ensure all incoming picks are stored in the canonical format.
*   **Golden Set Expansion:** Add more edge cases (e.g., obscure player props) to the golden set to prevent regression.
