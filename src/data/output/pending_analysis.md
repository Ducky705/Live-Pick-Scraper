# Analysis of 129 Pending Grades (Dry Run 2026-02-05)

## 1. Parser Failures (Props) - ~30-40 items
**Error:** `Stat ptso25.5 not found for LeBron`
**Cause:** The regex parser for props failed to handle single-letter abbreviations (`O` instead of `Over`) correctly, causing it to mash the line `25.5` into the stat key.
**Example:** `LeBron: Pts O 25.5` -> Parsed as Stat `ptso25.5`.
**Status:** **FIXED** (Step 368 updated `parser.py` regex). These should resolve in the next run.

## 2. Persistent Alias/League Issues - ~20-30 items
**Error:** `Could not resolve team` or `Game not found` (League: UNKNOWN)
**Examples:**
- `(6u) ers +4.5` (76ers)
- `5u Mavericks +8.5 v. Spurs`
- `Norte Dame +18` (Typo)
**Cause:**
- Even though aliases (`ers`, `mavericks`) were added, the **Extractor** often fails to identify the *League* (marked UNKNOWN).
- When League is UNKNOWN, the matching logic might be too strict or failing to prioritize alias lookup across all sports.
- **Action:**
    - Verify `enrich_picks` handles UNKNOWN league by searching all valid leagues.
    - Confirm `team_aliases.py` changes are actually being loaded/used.
    - `Norte Dame` typo was fixed in Step 305 (Status: **FIXED**).

## 3. Recursion Errors - ~10 items
**Error:** `maximum recursion depth exceeded`
**Examples:**
- `SPURS -1.5 1Q (-110)`
- `Lakers: 3P O 10.5`
- `SAS -1.5 1Q (-110)`
**Cause:** Likely a circular call in the `Matcher` or `PickParser` when handling specific edge cases (Period bets or Team Props).
**Action:** Investigate `Matcher.find_game` and `PickParser` for recursive loops.

## 4. Garbage/Noise Extraction - ~10-15 items
**Error:** Extraction of non-picks.
**Examples:**
- `-0 +3.5 unit sweep tonight ML`
- `of Profit Made in the NHL this season! ML`
- `[Corner Master Vip] ** 10,45 **`
- `None` (Null picks)
**Cause:** The AI or Rule-based extractor is too aggressive, picking up marketing text or metadata as picks.
**Action:**
- Improve `SemanticValidator` to reject text with "Profit", "Sweep", "Unit" (without team), or weird partials.
- Filter out `None` picks earlier in the pipeline.

## 5. College/Minor League Lookups - ~20 items
**Error:** `Game not found` for NCAAB/Tennis
**Examples:**
- `Drexel vs Campbell`
- `Michigan -24.5`
- `Yue Yuan ML` (Tennis)
**Cause:**
- College teams are numerous; exact naming matches in API (ESPN) vs Scraped text differ.
- Tennis coverage might be spotty in the Score Fetcher.
**Action:**
- Add more NCAA aliases if easy.
- Accept that Tennis/NCAAB coverage might be lower priority than NBA/NFL.

## 6. Multi-Leg/Parlay Failures
**Error:** `PENDING` due to one leg failing.
**Examples:** `(NBA) - Raptors -7.5 vs Bulls / 20-28`
**Cause:** If one leg is invalid/pending, the whole parlay is pending.
**Action:** Fixing the individual leg issues (Aliases, Parsing) will resolve these.

## Summary & Plan
1. **Verify Prop Fix:** The `ptso25.5` fix is done.
2. **Debug Recursion:** High priority. Locate the loop.
3. **Investigate "ers"/"Mavericks" failure:** Create a small test script to reproduce why `ers` + `UNKNOWN` league fails to match.
4. **Validation Filter:** Add filters for "Profit", "Sweep" to clean garbage.
