# Dry Run Analysis Report - 2026-02-23

**generated at:** 2026-02-24 13:37:06

## 1. Executive Summary
- **Target Date:** 2026-02-23 (Yesterday ET)
- **Total Time:** 7550.10s
- **Messages Scraped:** 416
- **Picks Extracted:** 426
- **Gradable Picks:** 261
- **Accuracy:** 49.04%

## 2. Extraction Quality (Raw vs Parsed)
- **Total Batches:** 96
- **Potential Raw Items:** 0
- **Successfully Parsed:** 908
- **Approx Parse Rate:** 0.00%
- **Empty Responses (No picks found):** 26

### Raw vs Parsed Comparison (Sample)
Showing first 5 batches with picks:

**Batch 0**
<details>
<summary>See Raw Output</summary>

```json
<thinking>
Message [1787]:
1. Denoising: The text includes promotional and contextual elements such as "🆓 **DAILY PICK (2/23/26) **", "NBA: SAC @ MEM (5:00 PM PST)**", "**✅ 25-19-3 Last 47 Free Plays 🔥🔥🔥", "1 Unit = 1–3% of Bankroll", and "**🕯". These are ignored as non-betting filler. The core betting line is "KINGS +4.5 (-120) (1.2U)".
2. Entity Translation: "KINGS" is shorthand for the Sacramento Kings NBA team. "+4.5" represents a point spread bet on the Kings to cover +4.5 points. "(-120)" are American odds indicating the payout. "(1.2U)" denotes a stake of 1.2 units.
3. Schema Mapping:
   - message_id: "1787"
   - capper_name: No explicit capper name (e.g., "SmartMoney") is present in the text; the header "DAILY PICK" is generic and not a capper name, so set to empty string.
   - sport: "NBA" inferred from "NBA: SAC @ MEM" in the context.
   - bet_type: "Spread" based on the "+4.5" pattern.
   - selection: "Kings +4.5" (using the team shorthand from the text, normalized to standard capitalization).
   - line: 4.5 (positive numeric value for the spread).
   - odds: -120 (American odds).
   - units: 1.2 (numeric stake).
   - confidence: 9.0 (default for explicit, clear patterns).
   - reasoning: "Explicit spread pattern with team name, line, odds, and units"
   - _source_text: "KINGS +4.5 (-120) (1.2U)" (exact substring from input).
4. Null Value Verification: capper_name is an empty string, which is valid as a string per schema. All other fields are populated with concrete values; no nulls required.

Message [1786]:
1. Denoising: The entire message is "**DAILY RECAP (2/22/26)** 🆙 New week let’s get back on track here ➡️ [**3-DAY FREE TRIAL**](https://www.winible.com/checkout/1538194817454985216?pid=1538194817463373825)". This is a recap and promotional link with no betting line, so all content is ignored.
2. Entity Translation: No betting-related entities present.
3. Schema Mapping: No picks to extract.
4. Null Value Verification: No picks generated, so no fields to verify.
</thinking>
{
  "picks": [
    {
      "message_id": "1787",
      "capper_name": "",
      "sport": "NBA",
      "bet_type": "Spread",
      "selection": "Kings +4.5",
      "line": 4.5,
      "odds": -120,
      "units": 1.2,
      "confidence": 9.0,
      "reasoning": "Explicit spread pattern with team name, line, odds, and units",
      "_source_text": "KINGS +4.5 (-120) (1.2U)"
    }
  ]
}
```
</details>

**Parsed Output:**
```json
[
  {
    "message_id": "1787",
    "capper_name": "",
    "league": "NBA",
    "type": "Spread",
    "pick": "Kings +4.5",
    "line": 4.5,
    "odds": -120,
    "units": 1.2,
    "confidence": 9.0,
    "reasoning": "Explicit spread pattern with team name, line, odds, and units",
    "id": "1787",
    "cn": "",
    "lg": "NBA",
    "ty": "Spread",
    "p": "Kings +4.5",
    "od": -120,
    "u": 1.2
  }
]
```

---

**Batch 5**
<details>
<summary>See Raw Output</summary>

```json
<thinking>
Message 13272:
1. Denoising: Text is "Mojo". This appears to be a capper name or header with no actual betting picks. Ignore.
2. Translation: No bets present.
3. Mapping: No picks to map.
4. Null Verification: No picks, so no variables to verify.

Message 13271:
1. Denoising: The text contains multiple cappers and picks. Ignore emojis (👉🏻, 🐋), context phrases like "20% POD", "(12-1 Max Run)", and promotional elements. Isolate the betting lines: "Houston ML -135 (20%)", "Mississippi Valley St +17 (2u Max)", "North Carolina +3 (1u)", "Houston -2 (1u)", "UTRGV vs McNeese St over 145.5 (1u)", "NBA Spurs +1 (1u)".
2. Translation:
   - "ML" → Moneyline
   - "CBB" → NCAAB (College Basketball)
   - "NBA" → NBA
   - Units: "2u Max" → 2.0, "1u" → 1.0. "(20%)" is not a numeric stake, so ignored for units.
   - "over 145.5" indicates a Total bet; team names "UTRGV" and "McNeese St" are attached as per rule.
3. Mapping:
   - "Russreallywins" is the capper for the first pick; sport inferred as NCAAB from preceding "NCAAB".
   - "Cblez" is the capper for subsequent picks; sport is NCAAB from "CBB" except for "NBA Spurs" which is explicitly NBA.
   - Bet types: ML, Spread, Total identified from patterns.
   - Selections: Team names with spread/over as given.
   - Lines: Numeric part of spread/total; null for ML.
   - Odds: Only specified for ML (-135); null otherwise.
   - Units: Extracted from "(Xu)" patterns; default 1.0 where not specified.
   - Confidence: Default 9.0 as not specified.
   - Reasoning: Assigned as "Explicit [bet_type]" based on pattern.
   - _source_text: Exact snippet from message.
4. Null Verification: For spread and total bets, odds are null (not provided). For ML, line is null. All picks have units (defaulted or explicit). Sport is correctly assigned per pick. Selection strings include team names and bet descriptors as required.

Message 13255:
1. Denoising: Promotional text with bonus offer and URL. No betting picks. Ignore.
2. Translation: No bets.
3. Mapping: None.
4. Null Verification: None.

Message 13250:
1. Denoising: Contains a Telegram link and channel name. No picks. Ignore.
2. Translation: None.
3. Mapping: None.
4. Null Verification: None.

Message 13273:
1. Denoising: Header listing capper names ("Learlocks, matchPointBets, Newmark & Caleb") with no picks. Ignore.
2. Translation: No bets.
3. Mapping: None.
4. Null Verification: None.
</thinking>
{
  "picks": [
    {
      "message_id": "13271",
      "capper_name": "Russreallywins",
      "sport": "NCAAB",
      "bet_type": "Moneyline",
      "selection": "Houston",
      "line": null,
      "odds": -135,
      "units": 1.0,
      "confidence": 9.0,
      "reasoning": "Explicit Moneyline",
      "_source_text": "Houston ML -135 (20%)"
    },
    {
      "message_id": "13271",
      "capper_name": "Cblez",
      "sport": "NCAAB",
      "bet_type": "Spread",
      "selection": "Mississippi Valley St +17",
      "line": 17.0,
      "odds": null,
      "units": 2.0,
      "confidence": 9.0,
      "reasoning": "Explicit spread",
      "_source_text": "Mississippi Valley St +17 (2u Max)"
    },
    {
      "message_id": "13271",
      "capper_name": "Cblez",
      "sport": "NCAAB",
      "bet_type": "Spread",
      "selection": "North Carolina +3",
      "line": 3.0,
      "odds": null,
      "units": 1.0,
      "confidence": 9.0,
      "reasoning": "Explicit spread",
      "_source_text": "North Carolina +3 (1u)"
    },
    {
      "message_id": "13271",
      "capper_name": "Cblez",
      "sport": "NCAAB",
      "bet_type": "Spread",
      "selection": "Houston -2",
      "line": 2.0,
      "odds": null,
      "units": 1.0,
      "confidence": 9.0,
      "reasoning": "Explicit spread",
      "_source_text": "Houston -2 (1u)"
    },
    {
      "message_id": "13271",
      "capper_name": "Cblez",
      "sport": "NCAAB",
      "bet_type": "Total",
      "selection": "UTRGV vs McNeese St over 145.5",
      "line": 145.5,
      "odds": null,
      "units": 1.0,
      "confidence": 9.0,
      "reasoning": "Explicit total",
      "_source_text": "UTRGV vs McNeese St over 145.5 (1u)"
    },
    {
      "message_id": "13271",
      "capper_name": "Cblez",
      "sport": "NBA",
      "bet_type": "Spread",
      "selection": "Spurs +1",
      "line": 1.0,
      "odds": null,
      "units": 1.0,
      "confidence": 9.0,
      "reasoning": "Explicit spread",
      "_source_text": "NBA Spurs +1 (1u)"
    }
  ]
}
```
</details>

**Parsed Output:**
```json
[
  {
    "message_id": "13271",
    "capper_name": "Russreallywins",
    "league": "NCAAB",
    "type": "Moneyline",
    "pick": "Houston ML",
    "line": null,
    "odds": -135,
    "units": 1.0,
    "confidence": 9.0,
    "reasoning": "Explicit Moneyline",
    "id": "13271",
    "cn": "Russreallywins",
    "lg": "NCAAB",
    "ty": "Moneyline",
    "p": "Houston",
    "od": -135,
    "u": 1.0
  },
  {
    "message_id": "13271",
    "capper_name": "Cblez",
    "league": "NCAAB",
    "type": "Spread",
    "pick": "Mississippi Valley St +17",
    "line": 17.0,
    "odds": null,
    "units": 2.0,
    "confidence": 9.0,
    "reasoning": "Explicit spread",
    "id": "13271",
    "cn": "Cblez",
    "lg": "NCAAB",
    "ty": "Spread",
    "p": "Mississippi Valley St +17",
    "od": null,
    "u": 2.0
  },
  {
    "message_id": "13271",
    "capper_name": "Cblez",
    "league": "NCAAB",
    "type": "Spread",
    "pick": "North Carolina +3",
    "line": 3.0,
    "odds": null,
    "units": 1.0,
    "confidence": 9.0,
    "reasoning": "Explicit spread",
    "id": "13271",
    "cn": "Cblez",
    "lg": "NCAAB",
    "ty": "Spread",
    "p": "North Carolina +3",
    "od": null,
    "u": 1.0
  },
  {
    "message_id": "13271",
    "capper_name": "Cblez",
    "league": "NCAAB",
    "type": "Spread",
    "pick": "Houston -2",
    "line": -2.0,
    "odds": null,
    "units": 1.0,
    "confidence": 9.0,
    "reasoning": "Explicit spread",
    "id": "13271",
    "cn": "Cblez",
    "lg": "NCAAB",
    "ty": "Spread",
    "p": "Houston -2",
    "od": null,
    "u": 1.0
  },
  {
    "message_id": "13271",
    "capper_name": "Cblez",
    "league": "NCAAB",
    "type": "Total",
    "pick": "Utrgv vs McNeese St over 145.5",
    "line": 145.5,
    "odds": null,
    "units": 1.0,
    "confidence": 9.0,
    "reasoning": "Explicit total",
    "id": "13271",
    "cn": "Cblez",
    "lg": "NCAAB",
    "ty": "Total",
    "p": "UTRGV vs McNeese St over 145.5",
    "od": null,
    "u": 1.0,
    "prop_side": "Over"
  },
  {
    "message_id": "13271",
    "capper_name": "Cblez",
    "league": "NBA",
    "type": "Spread",
    "pick": "Spurs +1",
    "line": 1.0,
    "odds": null,
    "units": 1.0,
    "confidence": 9.0,
    "reasoning": "Explicit spread",
    "id": "13271",
    "cn": "Cblez",
    "lg": "NBA",
    "ty": "Spread",
    "p": "Spurs +1",
    "od": null,
    "u": 1.0
  }
]
```

---

**Batch 8**
<details>
<summary>See Raw Output</summary>

```json
<thinking>
Message 11353:
1. Denoising: Text "Mojo" is a capper name or header with no betting pick. Ignored.
2. Translation: N/A
3. Mapping: N/A
4. Null Verification: No picks extracted.

Message 11351:
1. Denoising: Ignored emojis (👉🏻, 🐋), "20% POD", "(12-1 Max Run)" as filler. Extracted betting lines: "Houston ML -135", "Mississippi Valley St +17 (2u Max)", "North Carolina +3 (1u)", "Houston -2 (1u)", "UTRGV vs McNeese St over 145.5 (1u)", "NBA Spurs +1 (1u)".
2. Translation: 
   - "ML" -> Moneyline
   - "CBB" -> NCAAB
   - "u" -> units
   - Team abbreviations: "St" -> "State", "UTRGV" -> "UT Rio Grande Valley", "McNeese St" -> "McNeese State", but in selection use full names from schedule.
3. Mapping:
   - Capper names: "Russreallywins" for first pick, "Cblez" for subsequent picks.
   - Sports: "NCAAB" for first pick and next four, "NBA" for last pick.
   - Bet types: Moneyline for "ML", Spread for team+number, Total for "over".
   - Selections: Use full team names from schedule: "Houston", "Mississippi Valley State +17", "North Carolina +3", "Houston -2", "UT Rio Grande Valley vs McNeese State over 145.5", "San Antonio Spurs +1".
   - Lines: For spreads, numeric value with sign; for total, 145.5; for moneyline, null.
   - Odds: Only for first pick: -135; others null.
   - Units: From "(2u Max)" -> 2.0, "(1u)" -> 1.0; for first pick, no units, default 1.0.
   - Confidence: Default 9.0 for all.
   - Reasoning: "Explicit ML" for first, "Explicit spread" for spreads, "Explicit total" for total.
   - _source_text: Exact substrings as listed.
4. Null Verification: 
   - For moneyline, line is null (correct).
   - For spreads and total, odds are null (correct).
   - Units defaulted for first pick (1.0) since not specified.

Message 11350: Promo message, no picks. Ignored.
Message 11330: Link, no picks. Ignored.
Message 11354: List of capper names, no picks. Ignored.
</thinking>
{
  "picks": [
    {
      "message_id": "11351",
      "capper_name": "Russreallywins",
      "sport": "NCAAB",
      "bet_type": "Moneyline",
      "selection": "Houston",
      "line": null,
      "odds": -135,
      "units": 1.0,
      "confidence": 9.0,
      "reasoning": "Explicit ML",
      "_source_text": "Houston ML -135"
    },
    {
      "message_id": "11351",
      "capper_name": "Cblez",
      "sport": "NCAAB",
      "bet_type": "Spread",
      "selection": "Mississippi Valley State +17",
      "line": 17.0,
      "odds": null,
      "units": 2.0,
      "confidence": 9.0,
      "reasoning": "Explicit spread",
      "_source_text": "Mississippi Valley St +17 (2u Max)"
    },
    {
      "message_id": "11351",
      "capper_name": "Cblez",
      "sport": "NCAAB",
      "bet_type": "Spread",
      "selection": "North Carolina +3",
      "line": 3.0,
      "odds": null,
      "units": 1.0,
      "confidence": 9.0,
      "reasoning": "Explicit spread",
      "_source_text": "North Carolina +3 (1u)"
    },
    {
      "message_id": "11351",
      "capper_name": "Cblez",
      "sport": "NCAAB",
      "bet_type": "Spread",
      "selection": "Houston -2",
      "line": -2.0,
      "odds": null,
      "units": 1.0,
      "confidence": 9.0,
      "reasoning": "Explicit spread",
      "_source_text": "Houston -2 (1u)"
    },
    {
      "message_id": "11351",
      "capper_name": "Cblez",
      "sport": "NCAAB",
      "bet_type": "Total",
      "selection": "UT Rio Grande Valley vs McNeese State over 145.5",
      "line": 145.5,
      "odds": null,
      "units": 1.0,
      "confidence": 9.0,
      "reasoning": "Explicit total",
      "_source_text": "UTRGV vs McNeese St over 145.5 (1u)"
    },
    {
      "message_id": "11351",
      "capper_name": "Cblez",
      "sport": "NBA",
      "bet_type": "Spread",
      "selection": "San Antonio Spurs +1",
      "line": 1.0,
      "odds": null,
      "units": 1.0,
      "confidence": 9.0,
      "reasoning": "Explicit spread",
      "_source_text": "NBA Spurs +1 (1u)"
    }
  ]
}
```
</details>

**Parsed Output:**
```json
[
  {
    "message_id": "11351",
    "capper_name": "Russreallywins",
    "league": "NCAAB",
    "type": "Moneyline",
    "pick": "Houston ML",
    "line": null,
    "odds": -135,
    "units": 1.0,
    "confidence": 9.0,
    "reasoning": "Explicit ML",
    "id": "11351",
    "cn": "Russreallywins",
    "lg": "NCAAB",
    "ty": "Moneyline",
    "p": "Houston",
    "od": -135,
    "u": 1.0
  },
  {
    "message_id": "11351",
    "capper_name": "Cblez",
    "league": "NCAAB",
    "type": "Spread",
    "pick": "Mississippi Valley State +17",
    "line": 17.0,
    "odds": null,
    "units": 2.0,
    "confidence": 9.0,
    "reasoning": "Explicit spread",
    "id": "11351",
    "cn": "Cblez",
    "lg": "NCAAB",
    "ty": "Spread",
    "p": "Mississippi Valley State +17",
    "od": null,
    "u": 2.0
  },
  {
    "message_id": "11351",
    "capper_name": "Cblez",
    "league": "NCAAB",
    "type": "Spread",
    "pick": "North Carolina +3",
    "line": 3.0,
    "odds": null,
    "units": 1.0,
    "confidence": 9.0,
    "reasoning": "Explicit spread",
    "id": "11351",
    "cn": "Cblez",
    "lg": "NCAAB",
    "ty": "Spread",
    "p": "North Carolina +3",
    "od": null,
    "u": 1.0
  },
  {
    "message_id": "11351",
    "capper_name": "Cblez",
    "league": "NCAAB",
    "type": "Spread",
    "pick": "Houston -2",
    "line": -2.0,
    "odds": null,
    "units": 1.0,
    "confidence": 9.0,
    "reasoning": "Explicit spread",
    "id": "11351",
    "cn": "Cblez",
    "lg": "NCAAB",
    "ty": "Spread",
    "p": "Houston -2",
    "od": null,
    "u": 1.0
  },
  {
    "message_id": "11351",
    "capper_name": "Cblez",
    "league": "NCAAB",
    "type": "Total",
    "pick": "UT Rio Grande Valley vs McNeese State over 145.5",
    "line": 145.5,
    "odds": null,
    "units": 1.0,
    "confidence": 9.0,
    "reasoning": "Explicit total",
    "id": "11351",
    "cn": "Cblez",
    "lg": "NCAAB",
    "ty": "Total",
    "p": "UT Rio Grande Valley vs McNeese State over 145.5",
    "od": null,
    "u": 1.0,
    "prop_side": "Over"
  },
  {
    "message_id": "11351",
    "capper_name": "Cblez",
    "league": "NBA",
    "type": "Spread",
    "pick": "San Antonio Spurs +1",
    "line": 1.0,
    "odds": null,
    "units": 1.0,
    "confidence": 9.0,
    "reasoning": "Explicit spread",
    "id": "11351",
    "cn": "Cblez",
    "lg": "NBA",
    "ty": "Spread",
    "p": "San Antonio Spurs +1",
    "od": null,
    "u": 1.0
  }
]
```

---

**Batch 10**
<details>
<summary>See Raw Output</summary>

```json
<thinking>
Message [4201]:
1. Denoising: Header "🍀STONECOLD PICKS🍀" is marketing filler used to identify capper_name. The core betting signal is "Ugo Humbert -115🎾 1.5U". Emoji 🎾 indicates sport but is part of the text.
2. Entity Translation: "1.5U" translates to units = 1.5. "Ugo Humbert" is a valid tennis player name. "-115" is moneyline odds. Sport inferred as Tennis from emoji and context.
3. Schema Mapping: 
   - message_id: "4201"
   - capper_name: "STONECOLD" (from header)
   - sport: "Tennis"
   - bet_type: "Moneyline" (player name with odds)
   - selection: "Ugo Humbert"
   - line: null (moneyline has no spread line)
   - odds: -115
   - units: 1.5
   - confidence: 9.0 (default as not specified)
   - reasoning: "Explicit ML" (odds provided with player name)
   - _source_text: "Ugo Humbert -115🎾 1.5U" (exact substring from message)
4. Null Value Verification: All fields assigned; confidence and reasoning inferred but set.

Message [4200]:
1. Denoising: Text "Last 2 legs take place tomorrow🍀" has no valid betting pattern (no team/player names with numbers, no Over/Under, no ML). It's a contextual comment about previous bets, ignored.
2. Entity Translation: No entities.
3. Schema Mapping: No pick to map.
4. Null Value Verification: No pick, so no fields.
</thinking>
{
  "picks": [
    {
      "message_id": "4201",
      "capper_name": "STONECOLD",
      "sport": "Tennis",
      "bet_type": "Moneyline",
      "selection": "Ugo Humbert",
      "line": null,
      "odds": -115,
      "units": 1.5,
      "confidence": 9.0,
      "reasoning": "Explicit ML",
      "_source_text": "Ugo Humbert -115🎾 1.5U"
    }
  ]
}
```
</details>

**Parsed Output:**
```json
[
  {
    "message_id": "4201",
    "capper_name": "STONECOLD",
    "league": "TENNIS",
    "type": "Moneyline",
    "pick": "Ugo Humbert ML",
    "line": null,
    "odds": -115,
    "units": 1.5,
    "confidence": 9.0,
    "reasoning": "Explicit ML",
    "id": "4201",
    "cn": "STONECOLD",
    "lg": "TENNIS",
    "ty": "Moneyline",
    "p": "Ugo Humbert",
    "od": -115,
    "u": 1.5
  }
]
```

---

**Batch 11**
<details>
<summary>See Raw Output</summary>

```json
<thinking>
Message 2421: Empty content. No betting line present. Ignore.
Message 2420: "CASH IT 💰✅" – marketing filler/header. No mathematical wagering signal. Ignore.
Message 2419: Empty content. No betting line present. Ignore.
Message 2418: "NBA 🏀 Spurs +3 /-145/ 25 unit✅"
1. Denoising: Ignore "NBA 🏀" (sport indicator), emoji, and "✅" (noise). Isolate wagering signal: "Spurs +3 /-145/ 25 unit".
2. Translation: "Spurs +3" = spread bet on San Antonio Spurs with line +3.0. "/-145/" = odds -145. "25 unit" = stake 25 units.
3. Mapping: sport="NBA" (from context), bet_type="Spread", selection="Spurs +3", line=3.0, odds=-145, units=25, confidence=9 (default), reasoning="Explicit spread with odds and units", _source_text="NBA 🏀 Spurs +3 /-145/ 25 unit✅".
4. Null Verification: capper_name not explicitly stated in message; set to null. All other fields assigned.
Message 2417: "Free pick 💰" – generic header with no team/player/line. No valid bet. Ignore.
</thinking>
{
  "picks": [
    {
      "message_id": "2418",
      "capper_name": null,
      "sport": "NBA",
      "bet_type": "Spread",
      "selection": "Spurs +3",
      "line": 3.0,
      "odds": -145,
      "units": 25.0,
      "confidence": 9,
      "reasoning": "Explicit spread with odds and units",
      "_source_text": "NBA 🏀 Spurs +3 /-145/ 25 unit✅"
    }
  ]
}
```
</details>

**Parsed Output:**
```json
[
  {
    "message_id": "2418",
    "capper_name": null,
    "league": "NBA",
    "type": "Spread",
    "pick": "Spurs +3",
    "line": 3.0,
    "odds": -145,
    "units": 25.0,
    "confidence": 9.0,
    "reasoning": "Explicit spread with odds and units",
    "id": "2418",
    "cn": null,
    "lg": "NBA",
    "ty": "Spread",
    "p": "Spurs +3",
    "od": -145,
    "u": 25.0
  }
]
```

---


## 3. Grading Statistics
| Grade | Count |
| :--- | :---: |
| WIN | 128 |
| LOSS | 133 |
| PUSH | 0 |
| VOID | 1 |
| PENDING | 134 |
| ERROR | 30 |

## 4. Performance Breakdown
- **Extraction Yield:** 102.40% (Picks/Messages)

## 5. Missed/Error Cases (Diagnosis)
Found 164 items that could not be graded definitively.

| Pick | League | Reason/Details |
| :--- | :--- | :--- |
| Celtics -2 | NBA | Game not found |
| Ugo Humbert ML | TENNIS | Could not resolve team |
| Aaron Fox: Total Points Over 5.5 | NBA | Stat totalpoints not found for Aaron Fox |
| Celtics ML | NBA | Game not found |
| Wisconsin -1.5 | NCAAB | Game not found |
| NCAAB) Louisville ML / (NCAAB) McNeese ML | NCAAB | 'NoneType' object has no attribute 'raw_text' |
| Merrimack -6 | NCAAB | Game not found |
| Ohio State +10 | NCAAB | Could not resolve team |
| Wisconsin ML | NCAAB | Game not found |
| Southeast Louisiana +2 | NCAAB | Could not resolve team |
| Atp) Felix Auger Aliassime ML / (TENNIS) Jack Draper ML | ATP | 'NoneType' object has no attribute 'raw_text' |
| Rafael Jodar ML | ATP | Could not resolve team |
| TENNIS) Felix Auger Aliassme ML / (TENNIS) Jack Draper ML | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| Rafael Jodar ML | TENNIS | Could not resolve team |
| Houston Rockets: Total Points Under 121.5 | NCAAB | Stat totalpoints not found for Houston Rockets |
| Jarry +3.5 | TENNIS | Invalid scores |
| Norrie ML | TENNIS | Could not resolve team |
| TENNIS) Draper ML / (TENNIS) Medvedev ML | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| Lehecka ML | TENNIS | Could not resolve team |
| TENNIS) Bublik ML / (TENNIS) Khachanov ML | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| Popyrin ML | TENNIS | Could not resolve team |
| Tsitsipas ML | TENNIS | Could not resolve team |
| Griekspoor ML | TENNIS | Could not resolve team |
| Selekhmeteva ML | TENNIS | Could not resolve team |
| Walter Clayton Jr: Points+Assists Over 14.5 | NBA | Stat pointsassists not found for Walter Clayton Jr |
| Walter Clayton Jr: Points+Assists Over 14.5 | NCAAB | Game not found |
| TENNIS) Foki ML / (TENNIS) Vacherot ML | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| Demon 2:0 / Kovacevic +1.5 sets | TENNIS | Sho Shimabukuro: WIN / Hamad Medjedovic: PENDING |
| Hanfmann ML / Comesana +1.5 sets | TENNIS | Yannick Hanfmann: PENDING / Joao Lucas Reis Da Silva: PENDING |
| Adam Walton +2 | TENNIS | Could not resolve team |
| Adam Walton +2 | ATP | Game not found |
| TENNIS) Faa ML / (TENNIS) Draper ML | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| TENNIS) Kecmanovic ML / (TENNIS) Nakashima ML | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| Rafael Jodar ML | TENNIS | Could not resolve team |
| Kecmanovic Ml, Nakashima ML | TENNIS | Game not found |
| TENNIS) Felix Auger Aliassime ML / (TENNIS) Jack Draper MLP | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| Arthur Fils ML | TENNIS | Could not resolve team |
| Jenson Brooksby ML | TENNIS | Could not resolve team |
| Jakub Mensik ML | TENNIS | Could not resolve team |
| Walter Clayton Jr.: Total Rebounds + Assists Over 7.5 | NBA | Stat totalreboundsassists not found for Walter Clayton Jr. |
| Walter Clayton Jr: Total Rebounds + Assists Over 7.5 | NCAAB | Game not found |
| Stephon Castle: Total Points + Assists Over 19.5 | NCAAB | Game not found |
| NBA) S. Castle (Sas) Over 19.5 points / (NBA) assists | NBA | Stat points/(nba)assists not found for NBA) S. Castle (Sas) |
| NBA) W. Clayton Jr (Mem) Over 7.5 Rebounds / (NBA) assists | NBA | Stat rebounds/(nba)assists not found for NBA) W. Clayton Jr (Mem) |
| Faa -1.5 sets | TENNIS | Invalid scores |
| Prizmic ML / De Minaur -1.5 sets | TENNIS | Sho Shimabukuro: WIN / De Minaur: PENDING |
| Rakhimova ML | TENNIS | Could not resolve team |
| Aliassime -1.5 sets | ATP | Could not resolve team |
| Rakhimova ML | WTA | Game not found |
| NCAAB) Louisville ML / (NBA) Rockets ML | NCAAB | 'NoneType' object has no attribute 'raw_text' |
| Malik Monk (Sac) Over 16.5 points+assists | NBA | Stat pointsassists not found for Malik Monk (Sac) |
| Walter Clayton Jr: Points Over 10.5 | NCAAB | Game not found |
| Hawks ML / 76ers +14.5 | NBA | Atlanta Hawks: PENDING / 76ers: PENDING |
| Florida Atlantic 4.5 | NCAAB | Game not found |
| Norrie ML | TENNIS | Could not resolve team |
| TENNIS) Medvedev ML / (TENNIS) Bublik ML | ATP | 'NoneType' object has no attribute 'raw_text' |
| Hurkacz +2.5 | TENNIS | Could not resolve team |
| TENNIS) Khachanov ML / (TENNIS) Tsitsipas +1.5S | ATP | 'NoneType' object has no attribute 'raw_text' |
| TENNIS) Khachanov ML / (Atp) Majchrzak +1.5S | ATP | 'NoneType' object has no attribute 'raw_text' |
| Medvedev Ml, Bublik ML | TENNIS | Game not found |
| TENNIS) Khachanov ML / (TENNIS) Majchrzak +1.5S | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| Khachanov ML / Majchrzak +1.5 sets | TENNIS | Khachanov ML: PENDING / Kamil Majchrzak: PENDING |
| Rublev Ml, Bublik ML | TENNIS | Game not found |
| Brooksby +1.5 sets / Majchrzak +1.5 sets / Hurkacz +3.0 games / Tsitipas +1.5 sets / Bublik ML / Khachanov ML / Rublev ML / Medvedev ML | TENNIS | Jenson Brooksby: PENDING / Kamil Majchrzak: PENDING / Hurkacz: PENDING / Stefanos Tsitsipas: PENDING / Alexander Bublik: PENDING / Khachanov ML: PENDING / Rublev ML: PENDING / Medvedev ML: PENDING |
| Lehecka ML | TENNIS | Could not resolve team |
| Virtanen +2.0 | TENNIS | Invalid scores |
| TENNIS) Mpetshi ML / (TENNIS) Draper MLP | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| TENNIS) Hanfmann ML / (TENNIS) Comesana +1.5S | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| TENNIS) Foki ML / (TENNIS) Vacherot ML | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| TENNIS) Demon -1.5 sets / (TENNIS) Kovacevic +1.5S | TENNIS | Sho Shimabukuro: PENDING / Hamad Medjedovic: PENDING |
| Schoolkate +4.0 | TENNIS | Invalid scores |
| Selekhmeteva ML | TENNIS | Could not resolve team |
| TENNIS) Medvedev ML / (TENNIS) Bublik ML | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| Rublev ML / Tsitipas +1.5 sets | TENNIS | Rublev ML: PENDING / Tsitipas: PENDING |
| Brooksby ML | TENNIS | Could not resolve team |
| TENNIS) Medvedev ML / (TENNIS) Rublev ML / (TENNIS) Khachanov ML / (TENNIS) Bublik ML | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| TENNIS) Rublev ML / (TENNIS) Tsitipas +1.5S | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| Majchrzak +1.5 sets | TENNIS | Could not resolve team |
| Hurkacz +3.0 games | TENNIS | Could not resolve team |
| Bublik ML | TENNIS | Could not resolve team |
| Khachanov ML | TENNIS | Could not resolve team |
| Medvedev ML | TENNIS | Could not resolve team |
| Demon 2:0 / Kovacevic +1.5 sets | TENNIS | Sho Shimabukuro: WIN / Hamad Medjedovic: PENDING |
| Wemby: Pts vs Reb/Ast Over 37.5 | NBA | Stat ptsvsreb/ast not found for Wemby |
| TENNIS) Comesana / (TENNIS) Prizmic | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| G.Dimitrov -1.5 sets | TENNIS | Game not found |
| C.Norrie ML | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| A.Parks ML | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| V.Gracheva ML | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| TENNIS) Yastremska / (TENNIS) Potapov | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| Medvedev -4.5 | TENNIS | Could not resolve team |
| Khachanov -4.5 | TENNIS | Could not resolve team |
| Griekspoor ML | TENNIS | Could not resolve team |
| Tsitsipas ML | TENNIS | Could not resolve team |
| TENNIS) Bublik ML / (TENNIS) Rublev ML | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| Perricard -1.5 sets | TENNIS | Invalid scores |
| Wawrinka -4.5 | TENNIS | Could not resolve team |
| Faa -1.5 sets | TENNIS | Invalid scores |
| Nicolas Jarry +3.5 | ATP | Game not found |
| Nicolas Jarry +3.5 | TENNIS | Could not resolve team |
| Jarry +3.5 | ATP | Could not resolve team |
| Norrie ML | TENNIS | Could not resolve team |
| TENNIS) Draper ML / (TENNIS) Medvedev ML | ATP | 'NoneType' object has no attribute 'raw_text' |
| Nikola Bartunkova ML | TENNIS | Could not resolve team |
| Kamilia Rakhimova ML | TENNIS | Could not resolve team |
| Zizou Bergs ML | TENNIS | Could not resolve team |
| Wisconsin -3.5 | NCAAB | Game not found |
| Soccer) Fenerbahce ML / (Soccer) Sonderjyske vs Brondby Btts | SOCCER | 'NoneType' object has no attribute 'raw_text' |
| Celtics ML | NBA | Game not found |
| Popyrin vs Majchrzak Over 23 | TENNIS | Game not found |
| Zizou Bergs ML | TENNIS | Could not resolve team |
| Knicks -1 | NBA | Game not found |
| Aliassime -1.5 sets | TENNIS | Could not resolve team |
| Prizmic ML / De Minaur -1.5 sets | TENNIS | Vilius Gaubas: WIN / De Minaur: PENDING |
| Selekhmeteva ML | TENNIS | Could not resolve team |
| Rakhimova ML | TENNIS | Could not resolve team |
| TENNIS) Felix Auger Aliassime ML / (TENNIS) Jack Draper ML | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| Rafael Jodar ML | TENNIS | Could not resolve team |
| Barrios Vera +3.5 | TENNIS | Could not resolve team |
| Mpetshi Perricard +3.5 | TENNIS | Could not resolve team |
| Nicolas Jarry +3.5 | TENNIS | Could not resolve team |
| Jiri Lehecka ML | TENNIS | Could not resolve team |
| Rebecca Sramkova +6.5 | TENNIS | Could not resolve team |
| Rafael Jodar ML | TENNIS | Could not resolve team |
| Quentin Halys +3.5 | TENNIS | Could not resolve team |
| Nicolas Jarry +4.5 | TENNIS | Could not resolve team |
| Popyrin vs Majchrzak Over 23 | TENNIS | Game not found |
| Zizou Bergs ML | TENNIS | Could not resolve team |
| Quentin Halys +3.5 | TENNIS | Could not resolve team |
| Nicolas Jarry +3.5 | TENNIS | Could not resolve team |
| Moez Echargui +3.5 | TENNIS | Invalid scores |
| TENNIS) Broska ML / (TENNIS) Draper MLP | TENNIS | 'NoneType' object has no attribute 'raw_text' |
| Jarry +3.5 | TENNIS | Invalid scores |
| Bellucci +4.5 | TENNIS | Invalid scores |
| Humbert ML | TENNIS | Could not resolve team |
| Soto +5.5 | TENNIS | Could not resolve team |
| Mensik: Total Points Over 22.5 | TENNIS | Stat totalpoints not found for Mensik |
| Pacheco Mendez +5 | TENNIS | Invalid scores |
| Jarry ML | TENNIS | Could not resolve team |
| Selekhmeteva ML | TENNIS | Could not resolve team |
| Bondar ML | TENNIS | Could not resolve team |
| NC State -7.5 | NCAAB | Could not resolve team |
| Hornets Under 224.5 | NBA | Game not found |
| Hornets Under 223.5 | NBA | Game not found |
| Dayton -6.5 | NCAAB | Game not found |
| Tennessee 1.5 | NCAAB | Game not found |
| Blackhawks 1.5 | NHL | Game not found |
| Nuggets -1 | NBA | Game not found |
| Hornets -2.5 | NBA | Game not found |
| Yabusele: Points Over 8.5 | NBA | Stat pts not found for Yabusele |
| Kevin Porter: Total Points Over 27.5 | NBA | Stat totalpoints not found for Kevin Porter |
| Niederhauser: Total Points Over 13.5 | NBA | Game not found |
| Sandro Mamukelashvili: Total Points Over 12.5 | NBA | Stat totalpoints not found for Sandro Mamukelashvili |
| Sengun: Total Points Over 15.5 | NBA | Stat totalpoints not found for Sengun |
| Ty Jerome: Total Points Over 20.5 | NBA | Stat totalpoints not found for Ty Jerome |
| NC State 6.5 | NCAAB | Could not resolve team |
| Delaware 7.5 | NCAAB | Game not found |
| Navy -3.5 | NCAAB | Game not found |
| NC State 7.5 | NCAAB | Could not resolve team |
| Lightning -1 | NHL | Game not found |
| Knicks -5 | NBA | Game not found |
| Raptors 1.5 | NBA | Game not found |
| Clippers 2.5 | NBA | Game not found |
| Michigan state -6.5 | NCAAB | Could not resolve team |

## 6. Detailed Pick List
| Capper | League | Pick | Odds | Grade | Summary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Unknown | NBA | Kings +4.5 | -120 | ✅ WIN | Sacramento Kings 123.0 (+4.5=127.5) vs Memphis Grizzlies 114.0 |
| Unknown | NBA | Spurs +3 | -145 | ✅ WIN | San Antonio Spurs 114.0 (+3.0=117.0) vs Detroit Pistons 103.0 |
| Unknown | NCAAB | Louisville -3.5 | -192 | ❌ LOSS | Louisville Cardinals 74.0 (+-3.5=70.5) vs North Carolina Tar Heels 77.0 |
| Unknown | NBA | Grizzlies ML | None | ❌ LOSS | Memphis Grizzlies 114 - 123 Sacramento Kings |
| Unknown | WTA | Mandlik ML | -165 | ❌ LOSS | Sachia Vickery ? - ? Cadence Brace |
| Unknown | NBA | Detroit Pistons -1.5 | -110 | ❌ LOSS | Detroit Pistons 103.0 (+-1.5=101.5) vs San Antonio Spurs 114.0 |
| Unknown | NCAAB | Houston -1.5 | -110 | ❌ LOSS | Houston Cougars 56.0 (+-1.5=54.5) vs Kansas Jayhawks 69.0 |
| Unknown | NBA | Rockets vs Jazz Under 229.5 | -115 | ❌ LOSS | Total: 230.0 vs 229.5 |
| Unknown | NBA | Spurs +1.5 | -115 | ✅ WIN | San Antonio Spurs 114.0 (+1.5=115.5) vs Detroit Pistons 103.0 |
| Unknown | NCAAB | Kansas +1.5 | 100 | ✅ WIN | Kansas Jayhawks 69.0 (+1.5=70.5) vs Houston Cougars 56.0 |
| Unknown | NCAAB | Mcneese -11.5 | -110 | ❌ LOSS | McNeese Cowboys 75.0 (+-11.5=63.5) vs UT Rio Grande Valley Vaqueros 68.0 |
| Unknown | NBA | Cade Cunningham: Points+Assists Over 39 | -157 | ❌ LOSS | Cade Cunningham pointsassists: 10.0 vs 39.0 |
| Unknown | NBA | Celtics -2 | None | PENDING |  |
| Unknown | NCAAB | Houston ML | -135 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| Russreallywins | NCAAB | Houston ML | -135 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| Cblez | NCAAB | North Carolina +3 | -110 | ✅ WIN | North Carolina Tar Heels 77.0 (+3.0=80.0) vs Louisville Cardinals 74.0 |
| Cblez | NCAAB | Houston -2 | -101 | ❌ LOSS | Houston Cougars 56.0 (+-2.0=54.0) vs Kansas Jayhawks 69.0 |
| Cblez | NCAAB | UT Rio Grande Valley vs McNeese State over 145.5 | -110 | ❌ LOSS | Total: 143.0 vs 145.5 |
| Cblez | NBA | San Antonio Spurs +1 | -110 | ✅ WIN | San Antonio Spurs 114.0 (+1.0=115.0) vs Detroit Pistons 103.0 |
| Stonecold | TENNIS | Ugo Humbert ML | -115 | PENDING |  |
| Laformula | NBA | Aaron Fox: Total Points Over 5.5 | -140 | PENDING |  |
| Laformula | NBA | San Antonio Spurs vs Detroit Pistons Under 235.5 | -145 | ✅ WIN | Total: 217.0 vs 235.5 |
| Laformula | NCAAB | Houston Rockets vs Utah Jazz Over 224.5 | -165 | ❌ LOSS | Total: 125.0 vs 224.5 |
| Laformula | NBA | San Antonio vs Detroit Under 235.5 | -145 | ✅ WIN | Total: 217.0 vs 235.5 |
| Chamba | NCAAB | Louisville ML | -192 | ❌ LOSS | North Carolina Tar Heels 77 - 74 Louisville Cardinals |
| Chamba | NBA | Pistons ML | -118 | ❌ LOSS | Detroit Pistons 103 - 114 San Antonio Spurs |
| Chamba | NCAAB | Kansas Jayhawks +4 | None | ✅ WIN | Kansas Jayhawks 69.0 (+4.0=73.0) vs Houston Cougars 56.0 |
| Chamba | NBA | Celtics ML | None | PENDING |  |
| SBK | NBA | Spurs +2 | -120 | ✅ WIN | San Antonio Spurs 114.0 (+2.0=116.0) vs Detroit Pistons 103.0 |
| SBK | NCAAB | North Carolina +3.5 | -110 | ✅ WIN | North Carolina Tar Heels 77.0 (+3.5=80.5) vs Louisville Cardinals 74.0 |
| SBK | NCAAB | McNeese state H1 -6.5 | -120 | ✅ WIN | McNeese Cowboys 75.0 (+-6.5=68.5) vs UT Rio Grande Valley Vaqueros 68.0 |
| AlgoPicks | NBA | Spurs +2.5 | -110 | ✅ WIN | San Antonio Spurs 114.0 (+2.5=116.5) vs Detroit Pistons 103.0 |
| AFS | NCAAB | Louisville ML | -192 | ❌ LOSS | North Carolina Tar Heels 77 - 74 Louisville Cardinals |
| Travy | NBA | Spurs +3.5 | None | ✅ WIN | San Antonio Spurs 114.0 (+3.5=117.5) vs Detroit Pistons 103.0 |
| Travy | NCAAB | Wisconsin -1.5 | None | PENDING |  |
| Five star | NCAAB | Louisville ML | -192 | ❌ LOSS | North Carolina Tar Heels 77 - 74 Louisville Cardinals |
| Five star | NCAAB | Kansas Jayhawks +2.5 | None | ✅ WIN | Kansas Jayhawks 69.0 (+2.5=71.5) vs Houston Cougars 56.0 |
| Mazi | NCAAB | NCAAB) Louisville ML / (NCAAB) McNeese ML | -192 | ERROR |  |
| YourDailyCapper | NBA | Spurs +2 | -120 | ✅ WIN | San Antonio Spurs 114.0 (+2.0=116.0) vs Detroit Pistons 103.0 |
| Your Daily Capper | NCAAB | Louisville -2 | -120 | ❌ LOSS | Louisville Cardinals 74.0 (+-2.0=72.0) vs North Carolina Tar Heels 77.0 |
| Your Daily Capper | NCAAB | Nicholls State +4 | None | ✅ WIN | Nicholls Colonels 53.0 (+4.0=57.0) vs Lamar Cardinals 52.0 |
| Your Daily Capper | NCAAB | Kansas +2 | -110 | ✅ WIN | Kansas Jayhawks 69.0 (+2.0=71.0) vs Houston Cougars 56.0 |
| yourdailycapper | NCAAB | Merrimack -6 | None | PENDING |  |
| yourdailycapper | NCAAB | Ohio State +10 | None | PENDING |  |
| yourdailycapper | NCAAB | Wisconsin ML | None | PENDING |  |
| Your Daily Capper | NBA | Spurs ML | None | ✅ WIN | Detroit Pistons 103 - 114 San Antonio Spurs |
| SAS | NCAAB | Louisville -2.5 | -134 | ❌ LOSS | Louisville Cardinals 74.0 (+-2.5=71.5) vs North Carolina Tar Heels 77.0 |
| ISW | NCAAB | Lamar -3.5 | -110 | ❌ LOSS | Lamar Cardinals 52.0 (+-3.5=48.5) vs Nicholls Colonels 53.0 |
| ISW | NCAAB | Southeast Louisiana +2 | -110 | PENDING |  |
| ISW | NCAAB | Kansas vs Houston Under 138.5 | -112 | ✅ WIN | Total: 125.0 vs 138.5 |
| ISW | NCAAB | Kansas Under 138.5 | None | ✅ WIN | Total: 125.0 vs 138.5 |
| Smart Money Sports | NCAAB | Louisville Cardinals -2 | -115 | ❌ LOSS | Louisville Cardinals 74.0 (+-2.0=72.0) vs North Carolina Tar Heels 77.0 |
| Smart Money Sports | NCAAB | Kansas Jayhawks ML | 110 | ✅ WIN | Kansas Jayhawks 69 - 56 Houston Cougars |
| Smart Money Sports | NCAAB | Louisville -2 | -115 | ❌ LOSS | Louisville Cardinals 74.0 (+-2.0=72.0) vs North Carolina Tar Heels 77.0 |
| Smart Money Sports | NCAAB | Kansas ML | 110 | ✅ WIN | Kansas Jayhawks 69 - 56 Houston Cougars |
| P4D_Picks4Dayzzz | NCAAB | Louisville -3 | -110 | ❌ LOSS | Louisville Cardinals 74.0 (+-3.0=71.0) vs North Carolina Tar Heels 77.0 |
| P4D_Picks4Dayzzz | NCAAB | Houston -1 | -125 | ❌ LOSS | Houston Cougars 56.0 (+-1.0=55.0) vs Kansas Jayhawks 69.0 |
| P4D_Picks4Dayzzz | ATP | Atp) Felix Auger Aliassime ML / (TENNIS) Jack Draper ML | -133 | ERROR |  |
| P4D_Picks4Dayzzz | ATP | Rafael Jodar ML | 109 | PENDING |  |
| P4D_Picks4Dayzzz | TENNIS | TENNIS) Felix Auger Aliassme ML / (TENNIS) Jack Draper ML | -133 | ERROR |  |
| P4D_Picks4Dayzzz | TENNIS | Rafael Jodar ML | 109 | PENDING |  |
| Dormroom Degenerates | NBA | Spurs +2.5 | -110 | ✅ WIN | San Antonio Spurs 114.0 (+2.5=116.5) vs Detroit Pistons 103.0 |
| Dormroom Degenerates | NCAAB | Louisville vs Unc Over 162 | -108 | ❌ LOSS | Total: 151.0 vs 162.0 |
| Dormroom Degenerates | NCAAB | Kansas +2.5 | -105 | ✅ WIN | Kansas Jayhawks 69.0 (+2.5=71.5) vs Houston Cougars 56.0 |
| HammeringHank | NCAAB | Kansas +2.5 | -105 | ✅ WIN | Kansas Jayhawks 69.0 (+2.5=71.5) vs Houston Cougars 56.0 |
| HammeringHank | NCAAB | North Carolina +3.5 | -110 | ✅ WIN | North Carolina Tar Heels 77.0 (+3.5=80.5) vs Louisville Cardinals 74.0 |
| HammeringHank | NCAAB | SE Louisiana +1.5 | -110 | ❌ LOSS | SE Louisiana Lions 68.0 (+1.5=69.5) vs Texas A&M-Corpus Christi Islanders 73.0 |
| HammeringHank | NBA | Spurs +1.5 | -110 | ✅ WIN | San Antonio Spurs 114.0 (+1.5=115.5) vs Detroit Pistons 103.0 |
| Dquanpicks | NBA | Spurs +1.5 | -110 | ✅ WIN | San Antonio Spurs 114.0 (+1.5=115.5) vs Detroit Pistons 103.0 |
| Dquanpicks | NBA | Rockets -13 | -110 | ✅ WIN | Houston Rockets 125.0 (+-13.0=112.0) vs Utah Jazz 105.0 |
| CashCing | NBA | Kings +3 | -115 | ✅ WIN | Sacramento Kings 123.0 (+3.0=126.0) vs Memphis Grizzlies 114.0 |
| CashCing | NBA | Spurs +2 | -110 | ✅ WIN | San Antonio Spurs 114.0 (+2.0=116.0) vs Detroit Pistons 103.0 |
| CashCing | NCAAB | Louisville -2 | -120 | ❌ LOSS | Louisville Cardinals 74.0 (+-2.0=72.0) vs North Carolina Tar Heels 77.0 |
| CashCing | NCAAB | Kansas +2 | -110 | ✅ WIN | Kansas Jayhawks 69.0 (+2.0=71.0) vs Houston Cougars 56.0 |
| BettingWithBush | NCAAB | Houston -2 | -101 | ❌ LOSS | Houston Cougars 56.0 (+-2.0=54.0) vs Kansas Jayhawks 69.0 |
| BrandonTheProfit | NCAAB | Unc +4.5 | -115 | ✅ WIN | North Carolina Tar Heels 77.0 (+4.5=81.5) vs Louisville Cardinals 74.0 |
| BrandonTheProfit | NBA | Spurs +2 | -120 | ✅ WIN | San Antonio Spurs 114.0 (+2.0=116.0) vs Detroit Pistons 103.0 |
| Platinum Locks | NCAAB | Houston ML | -135 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| Sean Perry Wins VIP Clients | NBA | Kings vs Grizzlies Under 232.5 | None | ❌ LOSS | Total: 237.0 vs 232.5 |
| Tbsportsbetting | NBA | Spurs ML | None | ✅ WIN | Detroit Pistons 103 - 114 San Antonio Spurs |
| Tbsportsbetting | NCAAB | Louisville -3 | -110 | ❌ LOSS | Louisville Cardinals 74.0 (+-3.0=71.0) vs North Carolina Tar Heels 77.0 |
| Tbsportsbetting | NCAAB | Etam vs Hcu Over 138.5 | None | ✅ WIN | Total: 137.0 vs 138.5 |
| Tbsportsbetting | NCAAB | Houston ML | -135 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| Tbsportsbetting | NCAAB | East Texas A&M vs Houston Christian Over 138.5 | -108 | ❌ LOSS | Total: 137.0 vs 138.5 |
| Nba Max | NBA | Spurs +1.5 | -115 | ✅ WIN | San Antonio Spurs 114.0 (+1.5=115.5) vs Detroit Pistons 103.0 |
| Cbb Pod | NCAAB | Kansas +1.5 | 100 | ✅ WIN | Kansas Jayhawks 69.0 (+1.5=70.5) vs Houston Cougars 56.0 |
| CBB | NCAAB | Louisville -3.5 | -110 | ❌ LOSS | Louisville Cardinals 74.0 (+-3.5=70.5) vs North Carolina Tar Heels 77.0 |
| Duckinvestments | NCAAB | Houston Rockets: Total Points Under 121.5 | -112 | PENDING |  |
| Duckinvestments | NBA | Utah Jazz +13.5 | -120 | ❌ LOSS | Utah Jazz 105.0 (+13.5=118.5) vs Houston Rockets 125.0 |
| Duckinvestments | NBA | San Antonio Spurs vs Detroit Pistons Under 232.5 | -118 | ✅ WIN | Total: 217.0 vs 232.5 |
| Duckinvestments | NBA | Kings +3.0 | None | ✅ WIN | Sacramento Kings 123.0 (+3.0=126.0) vs Memphis Grizzlies 114.0 |
| duckinvestments | NBA | Detroit Pistons ML | -122 | ❌ LOSS | Detroit Pistons 103 - 114 San Antonio Spurs |
| duckinvestments | NBA | Sacramento Kings +3.0 | -110 | ✅ WIN | Sacramento Kings 123.0 (+3.0=126.0) vs Memphis Grizzlies 114.0 |
| duckinvestments | Other | Utah Jazz +13.5 vs San Antonio Spurs vs Detroit Pistons Under 232.5 | None | ✅ WIN | Total: 217.0 vs 232.5 |
| codycoverspreads | NBA | San Antonio Spurs ML | 100 | ✅ WIN | Detroit Pistons 103 - 114 San Antonio Spurs |
| codycoverspreads | NBA | Kings +5.5 | None | ✅ WIN | Sacramento Kings 123.0 (+5.5=128.5) vs Memphis Grizzlies 114.0 |
| codycoverspreads | NCAAB | Louisville ML | -192 | ❌ LOSS | North Carolina Tar Heels 77 - 74 Louisville Cardinals |
| codycoverspreads | NCAAB | McNeese ML | None | ✅ WIN | McNeese Cowboys 75 - 68 UT Rio Grande Valley Vaqueros |
| codycoverspreads | NBA | Sacramento Kings +5.5 | -110 | ✅ WIN | Sacramento Kings 123.0 (+5.5=128.5) vs Memphis Grizzlies 114.0 |
| codycoverspreads | NCAAB | Louisville Cardinals ML | -192 | ❌ LOSS | North Carolina Tar Heels 77 - 74 Louisville Cardinals |
| codycoverspreads | NFL | McNeese Cowboys ML | None | ✅ WIN | McNeese Cowboys 75 - 68 UT Rio Grande Valley Vaqueros |
| codycoverspreads | Other | Sacramento Kings +5.5 / Louisville Cardinals ML | None | ❌ LOSS | 2 legs |
| codycoverspreads | Other | San Antonio Spurs ML / Louisville Cardinals ML | None | ❌ LOSS | 2 legs |
| codycoverspreads | Other | San Antonio Spurs ML / McNeese Cowboys ML | None | ✅ WIN | 2 legs |
| Porter Picks | NBA | Kings +4 | -115 | ✅ WIN | Sacramento Kings 123.0 (+4.0=127.0) vs Memphis Grizzlies 114.0 |
| Porter Picks | NBA | San Antonio Spurs ML | 100 | ✅ WIN | Detroit Pistons 103 - 114 San Antonio Spurs |
| Porter Picks | NCAAB | Houston vs Kansas Under 138.5 | 110 | ✅ WIN | Total: 125.0 vs 138.5 |
| Porter Picks | NCAAB | Kansas ML | 110 | ✅ WIN | Kansas Jayhawks 69 - 56 Houston Cougars |
| PorterPicks | NBA | Sacramento Kings +4 | -110 | ✅ WIN | Sacramento Kings 123.0 (+4.0=127.0) vs Memphis Grizzlies 114.0 |
| Pick Don | NCAAB | Louisville ML | -192 | ❌ LOSS | North Carolina Tar Heels 77 - 74 Louisville Cardinals |
| Nicky Cashin | NBA | Spurs +1.5 | -110 | ✅ WIN | San Antonio Spurs 114.0 (+1.5=115.5) vs Detroit Pistons 103.0 |
| Nicky Cashin | NBA | Kings +4 | -115 | ✅ WIN | Sacramento Kings 123.0 (+4.0=127.0) vs Memphis Grizzlies 114.0 |
| Nicky Cashin | NCAAB | SE Louisiana +2.5 | -110 | ❌ LOSS | SE Louisiana Lions 68.0 (+2.5=70.5) vs Texas A&M-Corpus Christi Islanders 73.0 |
| Nicky Cashin | NCAAB | Louisville -2.5 | -134 | ❌ LOSS | Louisville Cardinals 74.0 (+-2.5=71.5) vs North Carolina Tar Heels 77.0 |
| Newmark | TENNIS | Jarry +3.5 | -110 | PENDING |  |
| Newmark | TENNIS | Norrie ML | -130 | PENDING |  |
| Newmark | TENNIS | TENNIS) Draper ML / (TENNIS) Medvedev ML | -141 | ERROR |  |
| Newmark | TENNIS | Lehecka ML | -110 | PENDING |  |
| Newmark | TENNIS | TENNIS) Bublik ML / (TENNIS) Khachanov ML | None | ERROR |  |
| Newmark | TENNIS | Popyrin ML | None | PENDING |  |
| Newmark | TENNIS | Tsitsipas ML | None | PENDING |  |
| Newmark | TENNIS | Griekspoor ML | None | PENDING |  |
| Analytics Capper | TENNIS | Selekhmeteva ML | -107 | PENDING |  |
| Analytics Capper | TENNIS | Volynets ML | -115 | ❌ LOSS | Sachia Vickery ? - ? Cadence Brace |
| Analytics Capper | TENNIS | Bondar ML | 110 | ❌ LOSS | Sachia Vickery ? - ? Cadence Brace |
| A1 Fantasy | NBA | Walter Clayton Jr: Points+Assists Over 14.5 | -115 | PENDING |  |
| A1 Fantasy | NBA | Cade Cunningham (Det) Over 25.5 points | -115 | ❌ LOSS | Cade Cunningham (Det) pts: 10.0 vs 25.5 |
| A1 Fantasy | NCAAB | Walter Clayton Jr: Points+Assists Over 14.5 | None | PENDING |  |
| Mojo Foki | TENNIS | TENNIS) Foki ML / (TENNIS) Vacherot ML | -152 | ERROR |  |
| Mojo Foki | TENNIS | Demon 2:0 / Kovacevic +1.5 sets | None | PENDING | 2 legs |
| Mojo Foki | TENNIS | Hanfmann ML / Comesana +1.5 sets | None | PENDING | 2 legs |
| Prop Joe | NCAAB | Houston -2 | -101 | ❌ LOSS | Houston Cougars 56.0 (+-2.0=54.0) vs Kansas Jayhawks 69.0 |
| Prop Joe | NCAAB | Northwestern State -3 | -110 | ✅ WIN | Northwestern State Demons 54.0 (+-3.0=51.0) vs Incarnate Word Cardinals 49.0 |
| Prop Joe | NCAAB | Nicholls State +3 | -110 | ✅ WIN | Nicholls Colonels 53.0 (+3.0=56.0) vs Lamar Cardinals 52.0 |
| Prop Joe | NBA | Spurs +1.5 | -110 | ✅ WIN | San Antonio Spurs 114.0 (+1.5=115.5) vs Detroit Pistons 103.0 |
| Prop Joe | TENNIS | Adam Walton +2 | -110 | PENDING |  |
| Prop Joe | ATP | Adam Walton +2 | -110 | PENDING |  |
| Picks 4 Dayzzz | NCAAB | Louisville -3 | -110 | ❌ LOSS | Louisville Cardinals 74.0 (+-3.0=71.0) vs North Carolina Tar Heels 77.0 |
| Picks 4 Dayzzz | NCAAB | Houston -1 | -125 | ❌ LOSS | Houston Cougars 56.0 (+-1.0=55.0) vs Kansas Jayhawks 69.0 |
| Picks 4 Dayzzz | TENNIS | TENNIS) Faa ML / (TENNIS) Draper ML | None | ERROR |  |
| Picks 4 Dayzzz | TENNIS | TENNIS) Kecmanovic ML / (TENNIS) Nakashima ML | None | ERROR |  |
| Picks 4 Dayzzz | TENNIS | Rafael Jodar ML | 109 | PENDING |  |
| Picks 4 Dayzzz | TENNIS | Faa Ml, Draper ML | None | ✅ WIN | Vilius Gaubas ? - ? Joao Lucas Reis Da Silva |
| Picks 4 Dayzzz | TENNIS | Kecmanovic Ml, Nakashima ML | None | PENDING |  |
| Picks 4 Dayzzz | TENNIS | TENNIS) Felix Auger Aliassime ML / (TENNIS) Jack Draper MLP | -133 | ERROR |  |
| Picks 4 Dayzzz | TENNIS | Arthur Fils ML | None | PENDING |  |
| Picks 4 Dayzzz | TENNIS | Jenson Brooksby ML | None | PENDING |  |
| Picks 4 Dayzzz | TENNIS | Jakub Mensik ML | None | PENDING |  |
| Mike Barner | NBA | Stephon Castle: Total Points + Assists Over 19.5 | -120 | ❌ LOSS | Stephon Castle totalpointsassists: 11.0 vs 19.5 |
| Mike Barner | NBA | Walter Clayton Jr.: Total Rebounds + Assists Over 7.5 | -125 | PENDING |  |
| Mike Barner | NCAAB | Walter Clayton Jr: Total Rebounds + Assists Over 7.5 | None | PENDING |  |
| Mike Barner | NCAAB | Stephon Castle: Total Points + Assists Over 19.5 | -120 | PENDING |  |
| Mike Barner | NBA | NBA) S. Castle (Sas) Over 19.5 points / (NBA) assists | -112 | PENDING |  |
| Mike Barner | NBA | NBA) W. Clayton Jr (Mem) Over 7.5 Rebounds / (NBA) assists | -115 | PENDING |  |
| Bankroll Bill | NCAAB | Houston ML | -135 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| Tennis Winners Only | TENNIS | Faa -1.5 sets | None | PENDING |  |
| Tennis Winners Only | TENNIS | Prizmic ML / De Minaur -1.5 sets | -116 | PENDING | 2 legs |
| Tennis Winners Only | TENNIS | Selekhmeteva ML | -107 | ✅ WIN | Sachia Vickery ? - ? Cadence Brace |
| Tennis Winners Only | TENNIS | Rakhimova ML | -150 | PENDING |  |
| TennisWinnersOnly | ATP | Aliassime -1.5 sets | -138 | PENDING |  |
| TennisWinnersOnly | WTA | Selekhmeteva ML | -107 | ✅ WIN | Iryna Shymanovich ? - ? Denislava Glushkova |
| TennisWinnersOnly | WTA | Rakhimova ML | -150 | PENDING |  |
| Anders Picks | NCAAB | Louisville -1.5 | 100 | ❌ LOSS | Louisville Cardinals 74.0 (+-1.5=72.5) vs North Carolina Tar Heels 77.0 |
| Anders Picks | NCAAB | Houston ML | -135 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| A11 Bets | NBA | Kings +4 | -115 | ✅ WIN | Sacramento Kings 123.0 (+4.0=127.0) vs Memphis Grizzlies 114.0 |
| A11 Bets | NCAAB | UT Rio Grande Valley +10.5 | None | ✅ WIN | UT Rio Grande Valley Vaqueros 68.0 (+10.5=78.5) vs McNeese Cowboys 75.0 |
| A11 Bets | NCAAB | Kansas 1-10 Win Margin | 110 | ✅ WIN | Kansas Jayhawks 69 - 56 Houston Cougars |
| A11 Bets | NBA | Louisville ML / (NBA) Rockets ML | None | ❌ LOSS | 2 legs |
| A11 Bets | NCAAB | NCAAB) Louisville +6.5 / (NCAAB) Kansas +7.5 | -110 | ✅ WIN | 2 legs |
| A11 Bets | NBA | Kings ML | None | ✅ WIN | Memphis Grizzlies 114 - 123 Sacramento Kings |
| A11 Bets | NCAAB | Kansas win margin 1-10 | 110 | ✅ WIN | Kansas Jayhawks 69 - 56 Houston Cougars |
| A11 Bets | Other | Louisville Ml, Rockets ML | None | ❌ LOSS | North Carolina Tar Heels 77 - 74 Louisville Cardinals |
| A11 Bets | NCAAB | Kansas ML | 110 | ✅ WIN | Kansas Jayhawks 69 - 56 Houston Cougars |
| A11 Bets | NCAAB | NCAAB) Louisville ML / (NBA) Rockets ML | -192 | ERROR |  |
| Bet Sharper | NCAAB | Louisville -2.5 | -134 | ❌ LOSS | Louisville Cardinals 74.0 (+-2.5=71.5) vs North Carolina Tar Heels 77.0 |
| Bet Sharper | NCAAB | Nicholls vs Lamar Under 145.5 | -110 | ✅ WIN | Total: 105.0 vs 145.5 |
| Bet Sharper | NCAAB | Houston ML | -135 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| Matthew P07 | NBA | Tobias Harris (Det): Points Over 13.5 | -112 | ❌ LOSS | Tobias Harris pts: 4.0 vs 13.5 |
| Matthew P07 | NBA | Amen Thompson (Hou): Points Over 16.5 | -108 | ✅ WIN | Amen Thompson pts: 20.0 vs 16.5 |
| Matthew P07 | NBA | Malik Monk (Sac) Over 16.5 points+assists | -112 | PENDING |  |
| Matthew P07 | NBA | Walter Clayton Jr (Mem): Points Over 10.5 | -115 | ❌ LOSS | Walter Clayton Jr. pts: 9.0 vs 10.5 |
| Matthew P07 | NCAAB | Walter Clayton Jr: Points Over 10.5 | None | PENDING |  |
| Bet Labs | NBA | Kings +4 | -110 | ✅ WIN | Sacramento Kings 123.0 (+4.0=127.0) vs Memphis Grizzlies 114.0 |
| Bet Labs | NCAAB | Louisville -3 | -110 | ❌ LOSS | Louisville Cardinals 74.0 (+-3.0=71.0) vs North Carolina Tar Heels 77.0 |
| TMS CBB Premium | NCAAB | Louisville -2.5 | -134 | ❌ LOSS | Louisville Cardinals 74.0 (+-2.5=71.5) vs North Carolina Tar Heels 77.0 |
| Vinny | NBA | Spurs +1.5 | -110 | ✅ WIN | San Antonio Spurs 114.0 (+1.5=115.5) vs Detroit Pistons 103.0 |
| Vinny | NBA | 1H Rockets -7.5 | None | ✅ WIN | 1H: Houston Rockets 68.0+-7.5=60.5 vs Utah Jazz 47.0 |
| Vinny | NCAAB | North Carolina +3.5 | -110 | ✅ WIN | North Carolina Tar Heels 77.0 (+3.5=80.5) vs Louisville Cardinals 74.0 |
| Vinny | NCAAB | Northwestern State ML | -120 | ✅ WIN | Northwestern State Demons 54 - 49 Incarnate Word Cardinals |
| Vinny | NCAAB | Houston ML | -135 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| Cesar | NBA | Kings +5.5 | None | ✅ WIN | Sacramento Kings 123.0 (+5.5=128.5) vs Memphis Grizzlies 114.0 |
| Cesar | NBA | Hawks ML / 76ers +14.5 | -140 | PENDING | 2 legs |
| GlitchPicks | NCAAB | Northwestern State ML | -120 | ✅ WIN | Northwestern State Demons 54 - 49 Incarnate Word Cardinals |
| GlitchPicks | NCAAB | Florida Atlantic 4.5 | -145 | PENDING |  |
| Golden Whale | NCAAB | Louisville ML | -192 | ❌ LOSS | North Carolina Tar Heels 77 - 74 Louisville Cardinals |
| Golden Whale | NCAAB | Kansas Jayhawks +2.5 | None | ✅ WIN | Kansas Jayhawks 69.0 (+2.5=71.5) vs Houston Cougars 56.0 |
| Jacav | NBA | 1H Rockets Over 59.5 | None | ✅ WIN | 1H Total: 115.0 vs 59.5 |
| Jacav | NBA | Kings +3.5 | None | ✅ WIN | Sacramento Kings 123.0 (+3.5=126.5) vs Memphis Grizzlies 114.0 |
| ProfiticsSports | NBA | Rockets: Total Points Over 118.5 | None | ✅ WIN | Rockets totalpoints: 125.0 vs 118.5 |
| ProfiticsSports | NCAAB | Louisville ML | -192 | ❌ LOSS | North Carolina Tar Heels 77 - 74 Louisville Cardinals |
| ProfiticsSports | NCAAB | Kansas +2.5 | -105 | ✅ WIN | Kansas Jayhawks 69.0 (+2.5=71.5) vs Houston Cougars 56.0 |
| ProfiticsSports | NCAAB | Northwestern State ML | -120 | ✅ WIN | Northwestern State Demons 54 - 49 Incarnate Word Cardinals |
| ProfiticsSports | NBA | Spurs +2.5 | -110 | ✅ WIN | San Antonio Spurs 114.0 (+2.5=116.5) vs Detroit Pistons 103.0 |
| ProfiticsSports | NBA | Spurs vs Pistons Under 238.5 | None | ✅ WIN | Total: 217.0 vs 238.5 |
| ProfiticsSports | NBA | Grizzlies ML | None | ❌ LOSS | Memphis Grizzlies 114 - 123 Sacramento Kings |
| ProfiticsSports | TENNIS | Norrie ML | -130 | PENDING |  |
| PickProphet | NCAAB | Louisville -2 | -135 | ❌ LOSS | Louisville Cardinals 74.0 (+-2.0=72.0) vs North Carolina Tar Heels 77.0 |
| PickProphet | NCAAB | East Texas A&M ML | -142 | ❌ LOSS | East Texas A&M Lions 68 - 69 Houston Christian Huskies |
| PickProphet | NBA | Kings vs Grizzlies Under 234.5 | -130 | ❌ LOSS | Total: 237.0 vs 234.5 |
| PatsPicks | NCAAB | Houston ML | -135 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| PatsPicks | NBA | Rockets -13.5 | -110 | ✅ WIN | Houston Rockets 125.0 (+-13.5=111.5) vs Utah Jazz 105.0 |
| PatsPicks | NBA | Pistons ML | -118 | ❌ LOSS | Detroit Pistons 103 - 114 San Antonio Spurs |
| PatsPicks | NCAAB | Unc +3.5 | -115 | ✅ WIN | North Carolina Tar Heels 77.0 (+3.5=80.5) vs Louisville Cardinals 74.0 |
| SharpInvestments | NBA | Spurs +2.5 | -110 | ✅ WIN | San Antonio Spurs 114.0 (+2.5=116.5) vs Detroit Pistons 103.0 |
| SharpInvestments | NCAAB | Louisville -2.5 | -134 | ❌ LOSS | Louisville Cardinals 74.0 (+-2.5=71.5) vs North Carolina Tar Heels 77.0 |
| TPD | NCAAB | Houston -1.5 | -110 | ❌ LOSS | Houston Cougars 56.0 (+-1.5=54.5) vs Kansas Jayhawks 69.0 |
| TPD | NCAAB | Louisville ML | -192 | ❌ LOSS | North Carolina Tar Heels 77 - 74 Louisville Cardinals |
| TheSharpSheets | NCAAB | Louisville -3.5 | -110 | ❌ LOSS | Louisville Cardinals 74.0 (+-3.5=70.5) vs North Carolina Tar Heels 77.0 |
| TheSharpSheets | Other | Jodar ML | 114 | ❌ LOSS | Northwestern State Demons 54 - 49 Incarnate Word Cardinals |
| TheSharpSheets | NBA | Kings +3.5 | None | ✅ WIN | Sacramento Kings 123.0 (+3.5=126.5) vs Memphis Grizzlies 114.0 |
| SeekingReturns | NBA | Memphis Grizzlies -2.5 | -118 | ❌ LOSS | Memphis Grizzlies 114.0 (+-2.5=111.5) vs Sacramento Kings 123.0 |
| SeekingReturns | NBA | Utah Jazz +13.5 | -120 | ❌ LOSS | Utah Jazz 105.0 (+13.5=118.5) vs Houston Rockets 125.0 |
| SeekingReturns | NCAAB | North Carolina Tar Heels +3.5 | -112 | ✅ WIN | North Carolina Tar Heels 77.0 (+3.5=80.5) vs Louisville Cardinals 74.0 |
| SeekingReturns | NCAAB | UT Rio Grande Valley Vaqueros +12.5 | -120 | ✅ WIN | UT Rio Grande Valley Vaqueros 68.0 (+12.5=80.5) vs McNeese Cowboys 75.0 |
| SeekingReturns | NCAAB | Incarnate Word Cardinals vs Northwestern State Demons Over 139.5 | -110 | ❌ LOSS | Total: 103.0 vs 139.5 |
| SeekingReturns | MLB | Nicholls Colonels vs Lamar Cardinals Over 14 | None | ❌ LOSS | Total: 9.0 vs 14.0 |
| Mojo | ATP | TENNIS) Medvedev ML / (TENNIS) Bublik ML | -137 | ERROR |  |
| Mojo | TENNIS | Hurkacz +2.5 | -150 | PENDING |  |
| Mojo | ATP | TENNIS) Khachanov ML / (TENNIS) Tsitsipas +1.5S | -145 | ERROR |  |
| Mojo | ATP | TENNIS) Khachanov ML / (Atp) Majchrzak +1.5S | None | ERROR |  |
| Mojo | TENNIS | Medvedev Ml, Bublik ML | -137 | PENDING |  |
| Mojo | TENNIS | TENNIS) Khachanov ML / (TENNIS) Majchrzak +1.5S | -145 | ERROR |  |
| Mojo | TENNIS | Khachanov ML / Majchrzak +1.5 sets | -147 | PENDING | 2 legs |
| Mojo | TENNIS | Rublev Ml, Bublik ML | -141 | PENDING |  |
| Mojo | TENNIS | Brooksby +1.5 sets / Majchrzak +1.5 sets / Hurkacz +3.0 games / Tsitipas +1.5 sets / Bublik ML / Khachanov ML / Rublev ML / Medvedev ML | -120 | PENDING | 8 legs |
| Mojo | TENNIS | Lehecka ML | -110 | PENDING |  |
| Mojo | TENNIS | Virtanen +2.0 | -150 | PENDING |  |
| Mojo | TENNIS | Medvedev Ml, Rublev Ml, Khachanov Ml, Bublik ML | 161 | ✅ WIN | 4 legs |
| Mojo | TENNIS | TENNIS) Mpetshi ML / (TENNIS) Draper MLP | -120 | ERROR |  |
| Mojo | TENNIS | TENNIS) Hanfmann ML / (TENNIS) Comesana +1.5S | -105 | ERROR |  |
| Mojo | TENNIS | Pellegrino ML | -120 | ❌ LOSS | Sachia Vickery ? - ? Cadence Brace |
| Mojo | TENNIS | TENNIS) Foki ML / (TENNIS) Vacherot ML | -152 | ERROR |  |
| Mojo | TENNIS | TENNIS) Demon -1.5 sets / (TENNIS) Kovacevic +1.5S | -167 | PENDING | 2 legs |
| Mojo | TENNIS | Schoolkate +4.0 | -150 | PENDING |  |
| Mojo | TENNIS | Selekhmeteva ML | -110 | PENDING |  |
| Mojo | TENNIS | Volynets ML | -115 | ❌ LOSS | Sachia Vickery ? - ? Cadence Brace |
| Mojo | TENNIS | Bondar ML | 110 | ❌ LOSS | Sachia Vickery ? - ? Cadence Brace |
| Mojo | TENNIS | TENNIS) Medvedev ML / (TENNIS) Bublik ML | -137 | ERROR |  |
| Mojo | TENNIS | Rublev ML / Tsitipas +1.5 sets | -145 | PENDING | 2 legs |
| Mojo | TENNIS | Brooksby ML | -120 | PENDING |  |
| Mojo | TENNIS | TENNIS) Medvedev ML / (TENNIS) Rublev ML / (TENNIS) Khachanov ML / (TENNIS) Bublik ML | 161 | ERROR |  |
| Mojo | TENNIS | TENNIS) Rublev ML / (TENNIS) Tsitipas +1.5S | -145 | ERROR |  |
| Mojo | TENNIS | Majchrzak +1.5 sets | None | PENDING |  |
| Mojo | TENNIS | Hurkacz +3.0 games | None | PENDING |  |
| Mojo | TENNIS | Bublik ML | None | PENDING |  |
| Mojo | TENNIS | Khachanov ML | None | PENDING |  |
| Mojo | TENNIS | Medvedev ML | None | PENDING |  |
| Mojo | TENNIS | Demon 2:0 / Kovacevic +1.5 sets | None | PENDING | 2 legs |
| BL | NCAAB | Louisville -3 | -110 | ❌ LOSS | Louisville Cardinals 74.0 (+-3.0=71.0) vs North Carolina Tar Heels 77.0 |
| BL | NBA | Kings +4 | -110 | ✅ WIN | Sacramento Kings 123.0 (+4.0=127.0) vs Memphis Grizzlies 114.0 |
| APP | NCAAB | Houston ML | -135 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| McBets | NCAAB | Louisville -2 | -120 | ❌ LOSS | Louisville Cardinals 74.0 (+-2.0=72.0) vs North Carolina Tar Heels 77.0 |
| TheGamblingGawd | NCAAB | Lamar ML | None | ❌ LOSS | Lamar Cardinals 52 - 53 Nicholls Colonels |
| TheGamblingGawd | NCAAB | Unc +2.5 | -110 | ✅ WIN | North Carolina Tar Heels 77.0 (+2.5=79.5) vs Louisville Cardinals 74.0 |
| TheGamblingGawd | NCAAB | Unc Over 161.5 | -108 | ❌ LOSS | Total: 151.0 vs 161.5 |
| TheGamblingGawd | NBA | Spurs ML | None | ✅ WIN | Detroit Pistons 103 - 114 San Antonio Spurs |
| TheGamblingGawd | NBA | Rockets Under 228.5 | None | ❌ LOSS | Total: 230.0 vs 228.5 |
| TheGamblingGawd | NCAAB | Houston Cougars ML | -148 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| TheGamblingGawd | NCAAB | Stephen F Austin -12.5 | None | ❌ LOSS | Stephen F. Austin Lumberjacks 73.0 (+-12.5=60.5) vs New Orleans Privateers 77.0 |
| TheGamblingGawd | NBA | Wemby: Pts vs Reb/Ast Over 37.5 | None | PENDING |  |
| Thisgirlbetz | TENNIS | TENNIS) Comesana / (TENNIS) Prizmic | 120 | ERROR |  |
| Thisgirlbetz | TENNIS | G.Dimitrov -1.5 sets | 100 | PENDING |  |
| Thisgirlbetz | TENNIS | C.Norrie ML | -120 | ERROR |  |
| Thisgirlbetz | TENNIS | A.Parks ML | -110 | ERROR |  |
| Thisgirlbetz | TENNIS | V.Gracheva ML | -145 | ERROR |  |
| Thisgirlbetz | TENNIS | TENNIS) Yastremska / (TENNIS) Potapov | None | ERROR |  |
| This Girl Betz | TENNIS | Medvedev -4.5 | None | PENDING |  |
| This Girl Betz | TENNIS | Khachanov -4.5 | None | PENDING |  |
| This Girl Betz | TENNIS | Griekspoor ML | None | PENDING |  |
| This Girl Betz | TENNIS | Tsitsipas ML | None | PENDING |  |
| This Girl Betz | TENNIS | TENNIS) Bublik ML / (TENNIS) Rublev ML | None | ERROR |  |
| This Girl Betz | TENNIS | Perricard -1.5 sets | None | PENDING |  |
| This Girl Betz | TENNIS | Wawrinka -4.5 | None | PENDING |  |
| This Girl Betz | TENNIS | Faa -1.5 sets | None | PENDING |  |
| TTW | NCAAB | Houston ML | -140 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| MatchPointBets | ATP | Nicolas Jarry +3.5 | -110 | PENDING |  |
| MatchPointBets | TENNIS | Murphy Cassone 2-0 | -125 | ✅ WIN | Vilius Gaubas ? - ? Joao Lucas Reis Da Silva |
| Match Point Bets | TENNIS | Nicolas Jarry +3.5 | -110 | PENDING |  |
| NewmarkTennis | ATP | Jarry +3.5 | -110 | PENDING |  |
| NewmarkTennis | TENNIS | Norrie ML | -130 | PENDING |  |
| NewmarkTennis | ATP | TENNIS) Draper ML / (TENNIS) Medvedev ML | -141 | ERROR |  |
| Learlocks | TENNIS | Nikola Bartunkova ML | 105 | PENDING |  |
| Learlocks | TENNIS | Kamilia Rakhimova ML | -135 | PENDING |  |
| Learlocks | TENNIS | Alex Barrena ML | 100 | ❌ LOSS | Sachia Vickery ? - ? Cadence Brace |
| Learlocks | SOCCER | Bologna ML | -110 | ✅ WIN | Bologna 1 - 0 Udinese |
| Lear Locks | TENNIS | Zizou Bergs ML | 100 | PENDING |  |
| Monumental | NCAAB | Wisconsin -3.5 | -110 | PENDING |  |
| TheSharpSquad | SOCCER | Soccer) Fenerbahce ML / (Soccer) Sonderjyske vs Brondby Btts | 103 | ERROR |  |
| LeesChosenPicks | NBA | Celtics ML | None | PENDING |  |
| Caleb Popyrin | TENNIS | Popyrin vs Majchrzak Over 23 | -110 | PENDING |  |
| Caleb Popyrin | TENNIS | Zizou Bergs ML | 100 | PENDING |  |
| Swami Site Bo’s Cager Line | NBA | Grizzlies Under 232 | None | ❌ LOSS | Total: 237.0 vs 232.0 |
| Pardon My Pick | NBA | San Antonio Spurs +1.5 | -115 | ✅ WIN | San Antonio Spurs 114.0 (+1.5=115.5) vs Detroit Pistons 103.0 |
| Pardon My Pick | NCAAB | Kansas +1.5 | 100 | ✅ WIN | Kansas Jayhawks 69.0 (+1.5=70.5) vs Houston Cougars 56.0 |
| Pardon My Pick | NCAAB | Louisville -3.5 | -110 | ❌ LOSS | Louisville Cardinals 74.0 (+-3.5=70.5) vs North Carolina Tar Heels 77.0 |
| Pardon My Pick | NCAAB | Kansas | 100 | ✅ WIN | Kansas Jayhawks 69 - 56 Houston Cougars |
| Marco D'Angelo | NCAAB | Houston ML | -135 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| Marco D’Angelo | NCAAB | Houston -1.5 | -110 | ❌ LOSS | Houston Cougars 56.0 (+-1.5=54.5) vs Kansas Jayhawks 69.0 |
| August Young | NBA | Spurs vs Pistons Under 232.5 | None | ✅ WIN | Total: 217.0 vs 232.5 |
| August Young | NBA | Jazz vs Rockets Under 229 | None | ❌ LOSS | Total: 230.0 vs 229.0 |
| August Young | NBA | Knicks -1 | None | PENDING |  |
| Trustmysystem | NCAAB | Louisville –2.5 | -192 | ❌ LOSS | North Carolina Tar Heels 77 - 74 Louisville Cardinals |
| Tenniswinneronly | TENNIS | Aliassime -1.5 sets | -138 | PENDING |  |
| Tenniswinneronly | TENNIS | Prizmic ML / De Minaur -1.5 sets | -116 | PENDING | 2 legs |
| Tenniswinneronly | TENNIS | Selekhmeteva ML | -107 | PENDING |  |
| Tenniswinneronly | TENNIS | Rakhimova ML | -150 | PENDING |  |
| P4D | TENNIS | TENNIS) Felix Auger Aliassime ML / (TENNIS) Jack Draper ML | -133 | ERROR |  |
| P4D | TENNIS | Rafael Jodar ML | 109 | PENDING |  |
| Seanperry | NBA | Kings vs Grizzlies Under 232.5 | None | ❌ LOSS | Total: 237.0 vs 232.5 |
| Wake and Cash | TENNIS | Barrios Vera +3.5 | None | PENDING |  |
| Wake and Cash | TENNIS | Mpetshi Perricard +3.5 | None | PENDING |  |
| Wake and Cash | TENNIS | Murphy Cassone 2-0 | -125 | ✅ WIN | Vilius Gaubas ? - ? Joao Lucas Reis Da Silva |
| Wake and Cash | TENNIS | Nicolas Jarry +3.5 | -110 | PENDING |  |
| Tail To Win | TENNIS | Jiri Lehecka ML | None | PENDING |  |
| Tail To Win | TENNIS | Rebecca Sramkova +6.5 | None | PENDING |  |
| Tail To Win | TENNIS | Rafael Jodar ML | 109 | PENDING |  |
| Tail To Win | TENNIS | Quentin Halys +3.5 | None | PENDING |  |
| Tail To Win | TENNIS | Nicolas Jarry +4.5 | None | PENDING |  |
| Caleb Picks | TENNIS | Popyrin vs Majchrzak Over 23 | -110 | PENDING |  |
| Caleb Picks | TENNIS | Zizou Bergs ML | 100 | PENDING |  |
| Caleb Picks | TENNIS | Quentin Halys +3.5 | None | PENDING |  |
| Caleb Picks | TENNIS | Nicolas Jarry +3.5 | -110 | PENDING |  |
| Out of Line Bets | TENNIS | Moez Echargui +3.5 | None | PENDING |  |
| Set Point Bets | TENNIS | TENNIS) Broska ML / (TENNIS) Draper MLP | None | ERROR |  |
| Set Point Bets | TENNIS | Jarry +3.5 | -110 | PENDING |  |
| Set Point Bets | TENNIS | Bellucci +4.5 | None | PENDING |  |
| Set Point Bets | TENNIS | Broska 2-0 | None | ✅ WIN | Rafael De Alba ? - ? Sho Shimabukuro |
| Set Point Bets | TENNIS | Alex De Minaur to make Acapulco semifinal | None | VOID |  |
| Set Point Bets | TENNIS | Humbert ML | None | PENDING |  |
| Set Point Bets | TENNIS | Navone ML | None | ✅ WIN | Iryna Shymanovich ? - ? Denislava Glushkova |
| Set Point Bets | TENNIS | Soto +5.5 | None | PENDING |  |
| Set Point Bets | TENNIS | Mensik: Total Points Over 22.5 | None | PENDING |  |
| Set Point Bets | TENNIS | Pacheco Mendez +5 | None | PENDING |  |
| Set Point Bets | TENNIS | Jarry ML | None | PENDING |  |
| Early Card | TENNIS | Selekhmeteva ML | -110 | PENDING |  |
| Early Card | TENNIS | Volynets ML | -115 | ❌ LOSS | Sachia Vickery ? - ? Cadence Brace |
| Early Card | TENNIS | Bondar ML | 110 | PENDING |  |
| SeanPerryWins | NBA | Kings vs Grizzlies Under 232.5 | None | ❌ LOSS | Total: 237.0 vs 232.5 |
| CodyCovers | NBA | Spurs ML | None | ✅ WIN | Detroit Pistons 103 - 114 San Antonio Spurs |
| CodyCovers | NBA | Kings +5.5 | None | ✅ WIN | Sacramento Kings 123.0 (+5.5=128.5) vs Memphis Grizzlies 114.0 |
| CodyCovers | NCAAB | Louisville ML | -192 | ❌ LOSS | North Carolina Tar Heels 77 - 74 Louisville Cardinals |
| CodyCovers | NCAAB | McNeese ML | None | ✅ WIN | McNeese Cowboys 75 - 68 UT Rio Grande Valley Vaqueros |
| Big Al | NCAAB | McNeese St -10.5 | -106 | ❌ LOSS | McNeese Cowboys 75.0 (+-10.5=64.5) vs UT Rio Grande Valley Vaqueros 68.0 |
| Ben Burns | NCAAB | McNeese St -10.5 | -106 | ❌ LOSS | McNeese Cowboys 75.0 (+-10.5=64.5) vs UT Rio Grande Valley Vaqueros 68.0 |
| Sia Nejad | NCAAB | Louisville -2 | -110 | ❌ LOSS | Louisville Cardinals 74.0 (+-2.0=72.0) vs North Carolina Tar Heels 77.0 |
| AJ Hoffman | NCAAB | Houston ML | -135 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| Spartan | NCAAB | Houston vs Kansas Under 138.0 | -112 | ✅ WIN | Total: 125.0 vs 138.0 |
| Spartan | NCAAB | Houston -1.5 | -115 | ❌ LOSS | Houston Cougars 56.0 (+-1.5=54.5) vs Kansas Jayhawks 69.0 |
| Spartan | NCAAB | NC State -7.5 | None | PENDING |  |
| Mike Lundin | NCAAB | Kansas +2.5 | -105 | ✅ WIN | Kansas Jayhawks 69.0 (+2.5=71.5) vs Houston Cougars 56.0 |
| Will Rogers | NCAAB | Houston ML | -125 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| Executive | NCAAB | Houston -1.5 | -110 | ❌ LOSS | Houston Cougars 56.0 (+-1.5=54.5) vs Kansas Jayhawks 69.0 |
| Executive | NCAAB | Houston -1.5 | -110 | ❌ LOSS | Houston Cougars 56.0 (+-1.5=54.5) vs Kansas Jayhawks 69.0 |
| Tony George | NBA | Jaylen Wells (Mem): Points Over 13.5 | -115 | ❌ LOSS | Jaylen Wells pts: 12.0 vs 13.5 |
| Tony George | NBA | Cade Cunningham (Det): Points Under 27.5 | -108 | ✅ WIN | Cade Cunningham (Det) pts: 10.0 vs 27.5 |
| Bob Balfe | NCAAB | Louisville -2.5 | -134 | ❌ LOSS | Louisville Cardinals 74.0 (+-2.5=71.5) vs North Carolina Tar Heels 77.0 |
| Jeff Michaels | NBA | Grizzlies: Total Points Over 118.5 | -112 | ❌ LOSS | Grizzlies totalpoints: 114.0 vs 118.5 |
| Jeff Michaels | NCAAB | Ttu Under 154.5 | None | ✅ WIN | Total: 141.0 vs 154.5 |
| Jeff Michaels | NBA | Hornets Under 224.5 | None | PENDING |  |
| Indian Cowboy | NCAAB | New Orleans +12.5 | None | ✅ WIN | New Orleans Privateers 77.0 (+12.5=89.5) vs Stephen F. Austin Lumberjacks 73.0 |
| Porter | NBA | Kings +4 | -115 | ✅ WIN | Sacramento Kings 123.0 (+4.0=127.0) vs Memphis Grizzlies 114.0 |
| Porter | NBA | Spurs ML | None | ✅ WIN | Detroit Pistons 103 - 114 San Antonio Spurs |
| Porter | NCAAB | Houston vs Kansas Under 138.5 | 110 | ✅ WIN | Total: 125.0 vs 138.5 |
| Sean Higgs | NCAAB | Kansas +2.5 | -105 | ✅ WIN | Kansas Jayhawks 69.0 (+2.5=71.5) vs Houston Cougars 56.0 |
| BettingGPT | NCAAB | Houston ML | -140 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| Sean Perry Supermax | NCAAB | Houston ML | -135 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| Ceaser | NBA | Kings +5.5 | None | ✅ WIN | Sacramento Kings 123.0 (+5.5=128.5) vs Memphis Grizzlies 114.0 |
| Wager Talk Will Rogers | NCAAB | Houston ML | -125 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| Tony T | NCAAB | Kansas +3.5 | None | ✅ WIN | Kansas Jayhawks 69.0 (+3.5=72.5) vs Houston Cougars 56.0 |
| Not monumental | NCAAB | Louisville -3.5 | -192 | ❌ LOSS | Louisville Cardinals 74.0 (+-3.5=70.5) vs North Carolina Tar Heels 77.0 |
| TCC | NBA | Grizzlies -2.5 | -125 | ❌ LOSS | Memphis Grizzlies 114.0 (+-2.5=111.5) vs Sacramento Kings 123.0 |
| TCC | NCAAB | Kansas +2.5 | -130 | ✅ WIN | Kansas Jayhawks 69.0 (+2.5=71.5) vs Houston Cougars 56.0 |
| TCC | NBA | Pistons -1.5 | -110 | ❌ LOSS | Detroit Pistons 103.0 (+-1.5=101.5) vs San Antonio Spurs 114.0 |
| Travy Whale | NBA | Spurs +3.5 | None | ✅ WIN | San Antonio Spurs 114.0 (+3.5=117.5) vs Detroit Pistons 103.0 |
| Afsports | NCAAB | Louisville ML | -192 | ❌ LOSS | North Carolina Tar Heels 77 - 74 Louisville Cardinals |
| Guess & Pray Fade | NCAAB | Kansas ML | 110 | ✅ WIN | Kansas Jayhawks 69 - 56 Houston Cougars |
| Guess & Pray Fade | NCAAB | Nicholls +2.5 | None | ✅ WIN | Nicholls Colonels 53.0 (+2.5=55.5) vs Lamar Cardinals 52.0 |
| Guess & Pray Fade | NCAAB | Louisville -3.5 | -110 | ❌ LOSS | Louisville Cardinals 74.0 (+-3.5=70.5) vs North Carolina Tar Heels 77.0 |
| Guess & Pray Fade | NBA | Spurs ML | None | ✅ WIN | Detroit Pistons 103 - 114 San Antonio Spurs |
| Guess & Pray Fade | NBA | Kings Under 232.5 | None | ❌ LOSS | Total: 237.0 vs 232.5 |
| Guess & Pray Fade | NBA | Jazz Over 229.5 | None | ✅ WIN | Total: 230.0 vs 229.5 |
| ErichLocks | NCAAB | Louisville -2.5 | -134 | ❌ LOSS | Louisville Cardinals 74.0 (+-2.5=71.5) vs North Carolina Tar Heels 77.0 |
| Lords | NCAAB | Houston ML | -135 | ❌ LOSS | Kansas Jayhawks 69 - 56 Houston Cougars |
| Swami Site Bo’s | NBA | Memphis Grizzlies vs Sacramento Kings Under 232 | -108 | ❌ LOSS | Total: 237.0 vs 232.0 |
| Insider | NBA | Detroit Pistons ML | -122 | ❌ LOSS | Detroit Pistons 103 - 114 San Antonio Spurs |
| Don | NCAAB | Louisville ML | -192 | ❌ LOSS | North Carolina Tar Heels 77 - 74 Louisville Cardinals |
| BetBros | NCAAB | Kansas ML | 110 | ✅ WIN | Kansas Jayhawks 69 - 56 Houston Cougars |
| Austin Young | NCAAB | Louisville vs North Carolina Over 162 | -110 | ❌ LOSS | Total: 151.0 vs 162.0 |
| Magnum / TheVegasWhale | NBA | Hornets Under 223.5 | None | PENDING |  |
| BataBingBets | NCAAB | Dayton -6.5 | None | PENDING |  |
| BataBingBets | NCAAB | Tennessee 1.5 | None | PENDING |  |
| BataBingBets | NHL | Blackhawks 1.5 | None | PENDING |  |
| Miguel Conneeke | NCAAB | Kansas +2.5 | -105 | ✅ WIN | Kansas Jayhawks 69.0 (+2.5=71.5) vs Houston Cougars 56.0 |
| Spreadkiller | NBA | Nuggets -1 | None | PENDING |  |
| Spreadkiller | NBA | Hornets -2.5 | None | PENDING |  |
| Barner | NBA | Nique Clifford: Points Over 13.5 | None | ❌ LOSS | Nique Clifford pts: 12.0 vs 13.5 |
| Barner | NBA | Yabusele: Points Over 8.5 | None | PENDING |  |
| Barner | NBA | Kevin Porter: Total Points Over 27.5 | None | PENDING |  |
| Barner | NBA | Cade Cunningham: Total Points Over 38.5 | None | ❌ LOSS | Cade Cunningham totalpoints: 10.0 vs 38.5 |
| Barner | NBA | Niederhauser: Total Points Over 13.5 | None | PENDING |  |
| Barner | NBA | Sandro Mamukelashvili: Total Points Over 12.5 | -112 | PENDING |  |
| Barner | NBA | Sengun: Total Points Over 15.5 | None | PENDING |  |
| Barner | NBA | Ty Jerome: Total Points Over 20.5 | None | PENDING |  |
| Bookmaker | NCAAB | NC State 6.5 | None | PENDING |  |
| Bookmaker | NCAAB | Delaware 7.5 | None | PENDING |  |
| Bookmaker | NCAAB | Northern Arizona -7.5 | None | ❌ LOSS | Arizona Diamondbacks 5.0 (+-7.5=-2.5) vs Cleveland Guardians 9.0 |
| Bookmaker | NCAAB | Navy -3.5 | None | PENDING |  |
| Konarski | NCAAB | Belmont -1 | None | ❌ LOSS | SE Louisiana Lions 68.0 (+-1.0=67.0) vs Texas A&M-Corpus Christi Islanders 73.0 |
| Konarski | NCAAB | NC State 7.5 | None | PENDING |  |
| Smudger | NCAAB | NCAAB) Unc 10.5 ML / (NCAAB) Houston 7.5 ML | 160 | ❌ LOSS | 2 legs |
| NewYorkSharps | NHL | Lightning -1 | None | PENDING |  |
| Marshall | NBA | Knicks -5 | None | PENDING |  |
| Marshall | NBA | Raptors 1.5 | None | PENDING |  |
| Marshall | NBA | Spurs -9.5 | None | ✅ WIN | San Antonio Spurs 114.0 (+-9.5=104.5) vs Detroit Pistons 103.0 |
| Marshall | NBA | Clippers 2.5 | None | PENDING |  |
| SpreadBundy POD | NCAAB | Michigan state -6.5 | None | PENDING |  |
