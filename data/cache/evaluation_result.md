# EVALUATION REPORT

### DIMENSION SCORES

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| 1. Extraction Accuracy | 8/10 | Missed 2 valid picks out of ~15 (Messages 31567, 31565). No false positives. |
| 2. Pick Formatting | 10/10 | Formats are perfectly aligned with specification. |
| 3. Classification Accuracy | 10/10 | Leagues and bet types correctly identified. |
| 4. Capper Attribution | 10/10 | Capper names correctly extracted from text headers. |
| 5. Odds & Units Extraction | 10/10 | Correctly handled absence of odds/units (defaults used). |
| 6. Data Completeness | 10/10 | All structured fields (line, market, subject) populated. |
| **OVERALL** | **58/60** | **Excellent performance, with minor drop in recall.** |

---

### MISSED PICKS

1. **Message ID:** 31567
   - **Missed Pick:** Playbook NBA LA Lakers +3.5
   - **Expected Output:** `{"capper_name": "Playbook", "league": "NBA", "type": "Spread", "pick": "LA Lakers +3.5", "line": 3.5}`

2. **Message ID:** 31565
   - **Missed Pick:** Marc Lawrence NCAAB Cal Baptist -3
   - **Expected Output:** `{"capper_name": "Marc Lawrence", "league": "NCAAB", "type": "Spread", "pick": "Cal Baptist -3", "line": -3.0}`

---

### FALSE POSITIVES / HALLUCINATIONS

*None detected.*

---

### CLASSIFICATION ERRORS

*None detected.*

---

### FORMATTING ERRORS

*None detected.*

---

### SUMMARY

The scraper demonstrates high precision (100%) but slightly imperfect recall (~87%). It correctly ignored all promotional/spam messages and perfectly formatted the picks it found, including complex structured data like lines and subjects. The only issue is the omission of two valid picks (Messages 31567 and 31565) which follow the exact same pattern as successfully extracted picks. This suggests a potential issue in batch processing, context window limits, or over-aggressive deduplication rather than a parsing failure.

---

# ANALYSIS OF GRADE

The high score (58/60) indicates that the core parsing logic (Prompt Engineering + Validator) is robust. The specific breakdown reveals:

1.  **Reliability:** The formatting and structured data extraction are rock solid. This is often the hardest part of LLM extraction, so achieving 10/10 here is a significant win.
2.  **The "Missing Pick" Anomaly:** The missed picks are structurally identical to the captured ones (Header Name + League + Pick). 
    - *Hypothesis 1 (Deduplication):* Pick 31565 ("Cal Baptist -3") is identical to Pick 5 (Message 31585). The system might have deduped strictly by content, ignoring the different capper name. This is a likely cause for 31565.
    - *Hypothesis 2 (Batching/Truncation):* Message 31567 (Lakers) is unique. Its absence is more puzzling. It appears near the end of the processed list. If the AI response was truncated or if the batch size logic dropped the last item, this could explain it.

**Actionable Insights:**
- **Check Deduplication Logic:** Verify if `deduplicate_by_capper` is merging picks with the same content but different cappers. It should ONLY merge if Capper AND Pick AND Message ID (approx) match, or if it's meant to merge same picks from different sources (which might be the case here if "Spartan" and "Marc Lawrence" are selling the same play, but they should usually be kept distinct if the names are different).
- **Investigate Message 31567:** Since it's not a duplicate, its loss suggests a pipeline drop. Check logs for "Batch failed" or similar errors for the last batch.
