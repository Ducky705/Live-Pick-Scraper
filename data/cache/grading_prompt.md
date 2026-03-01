# SPORTS BETTING SCRAPER OUTPUT EVALUATION

## TASK
You are a **strict evaluator** for an automated sports betting pick scraper. Your job is to grade how well the AI parser extracted and formatted picks from raw Telegram messages against the **official specification** provided below.

**Date Analyzed:** 2026-01-23
**Messages Processed:** 2
**Picks Extracted:** 6

---

## OFFICIAL FORMAT SPECIFICATION

**IMPORTANT:** All picks MUST conform to this specification. Use this as your ground truth for grading.

### **Sports Pick Data Formatting Guide**

### **1. Introduction**

This document specifies the standard format for storing sports betting picks in the `picks_test` Supabase table. Adherence to this guide is mandatory to ensure data consistency, clarity, and parsability for all front-end, back-end, and analytical applications.

### **2. Standardized `league` Column Values**

Use the following official uppercase abbreviations for the `league` column. This list also includes special values for handling multi-league parlays and unknown leagues.

| `league` | Description |
| :---- | :---- |
| `NFL` | National Football League |
| `NCAAF` | NCAA Football |
| `NBA` | National Basketball Assoc. |
| `NCAAB` | NCAA Basketball |
| `WNBA` | Women's National Basketball |
| `MLB` | Major League Baseball |
| `NHL` | National Hockey League |
| `EPL` | English Premier League |
| `MLS` | Major League Soccer |
| `UCL` | UEFA Champions League |
| `UFC` | Ultimate Fighting Championship |
| `PFL` | Professional Fighters League |
| `TENNIS` | ATP / WTA Tours |
| `PGA` | PGA Tour |
| `F1` | Formula 1 |
| `Other` | Parlay with multiple leagues |
| `Other` | League is not listed or is unknown |

### **3. Standardized `type` Column Values**

The `type` column must use one of the following values to categorize the bet.

| `type` | Description |
| :---- | :---- |
| `Moneyline` | A bet on which team or competitor will win the event outright. |
| `Spread` | A bet on the margin of victory (e.g., Point Spread, Run Line, Puck Line). |
| `Total` | A bet on the combined score of both teams (Over/Under). |
| `Player Prop` | A bet on a specific player's statistical performance. |
| `Team Prop` | A bet on a specific team's statistical performance (includes Team Totals). |
| `Game Prop` | A bet on a specific game event not directly tied to the final outcome. |
| `Period` | A bet specific to a defined segment of a game (e.g., Quarter, Half, Period). |
| `Parlay` | A single bet linking two or more individual wagers. |
| `Teaser` | A parlay where point spreads or totals are adjusted in the bettor's favor. |
| `Future` | A long-term bet on a future event (e.g., Championship winner). |
| `Unknown` | Used when the bet type cannot be determined from the source text. |

### **4. `pick_value` Format Specification**

The format of the `pick_value` string is strictly determined by the bet `type`.

**Key Formatting Rules:**

* **Pick vs. Odds:** The `pick_value` string describes *what* is being bet on. The price/payout (e.g., -110, +150) must **only** be stored in the `odds_american` column.
* **Number Formatting:** For all numerical values, omit trailing `.0` decimals. Use `48` instead of `48.0`, but retain decimals where necessary (e.g., `48.5`).
* **Unknown Type Handling:** If the `type` is set to `Unknown`, the `pick_value` column must contain the **original, unformatted text** of the pick.

#### **`Moneyline`**

* **Format:** `Team or Competitor Name ML`
* **Example:** `Los Angeles Lakers ML`

#### **`Spread`**

* **Format:** `Team Name [space] Point Spread`
* **Example:** `Green Bay Packers -7.5`

#### **`Total`**

* **Format:** `Team A vs Team B Over/Under Number`
* **Note:** The matchup `Team A vs Team B` is required context. The team on the right is typically the home team. If one team is unknown, use "Unknown".
* **Example:** `Lakers vs Celtics Over 215.5`, `Rutgers vs Unknown Under 143.5`

#### **`Player Prop`**

* **Format:** `Player Name: Stat Over/Under/Value`
* **Standard Stat Abbreviations:**
  * **Basketball:** `Pts`, `Reb`, `Ast`, `Blk`, `Stl`, `3PM`, `Pts+Reb+Ast` (or `PRA`)
  * **Football:** `PassYds`, `RushYds`, `RecYds`, `PassTD`, `Rec`, `Comp`
  * **Baseball:** `K`, `H`, `HR`, `RBI`, `TotalBases`
  * **Hockey:** `SOG`, `G`, `A`, `P`
* **Example:** `LeBron James: Pts Over 25.5`

#### **`Team Prop`**

* **Format:** `Team Name: Stat Over/Under/Value`
* **Example:** `Dallas Cowboys: Total Points Over 27.5`

#### **`Game Prop`**

* **Format:** `Description of Prop: Value`
* **Example:** `Fight to go the Distance: No`

#### **`Period`**

* **Format:** `Period Identifier [Standard Bet Format]`
* **Period Identifiers:** `1H`, `2H`, `1Q`, `2Q`, `3Q`, `4Q`, `P1`, `P2`, `P3`, `F5`, `F3`, `F1`, `Set 1`
* **CRITICAL DETECTION RULE:** If pick text contains ANY of these phrases, type MUST be `Period`:
  * "First Half", "Second Half", "1st Half", "2nd Half", "1H", "2H"
  * "1Q", "2Q", "3Q", "4Q", "First Quarter", etc.
  * "First 5", "F5", "First 3", "F3" (baseball)
  * "P1", "P2", "P3" (hockey periods)
* **Examples:** 
  * `1H NYK vs BOS Total Over 110.5`
  * `1Q Thunder -2`
  * `1H George Mason -6` (NOT "George Mason First Half -6")

#### **`Tennis` (TENNIS League - Special Rules)**

Tennis picks use different formats than team sports:

* **Moneyline:** `Player Name ML`
  * Example: `Tommy Paul ML`, `Sinner ML`
* **Set Spread:** `Player Name +/-X.X sets`
  * Example: `Giron +1.5 sets`, `Paul -1.5 sets`
* **Game Spread (Match):** `Player Name +/-X.X games`
  * Example: `Rune +3.5 games`
* **Game Spread (Set):** `Player Name Set X +/-X.X games`
  * Example: `Mpetshi S1 +1.5 games`
* **Total Games:** `Player A vs Player B Over/Under X.X games`
  * Example: `Paul vs Rune Over 22.5 games`
* **Set Winner:** `Player Name to win Set X`
  * Example: `Sinner to win Set 1`

#### **`Parlay` / `Teaser` (UPDATED FORMAT)**

* **Format:** `(Leg 1 League) Details [space]/[space] (Leg 2 League) Details [space]/...`
* **Rule:** Each leg is described using its standard format (e.g., `Team -X.5`, `Team ML`) and separated by `/`. The bet type (Spread, ML, etc.) is **not** included in the leg description.
* **League Prefix:** Prefixing each leg with its league in parentheses (e.g., `(NFL)`) is **mandatory**.
* **Teasers:** For Teasers, include the teaser points and the league: `(Teaser 6pt NFL) ...`
* **Parlay Examples:**
  * `(NFL) Dallas Cowboys -10.5 / (NFL) San Francisco 49ers ML`
  * `(NFL) Jalen Hurts: RushYds Over 48.5 / (NFL) A.J. Brown: RecYds Over 80.5`
  * `(NFL) Cowboys -10.5 / (NBA) Lakers ML`
* **Teaser Example (6-Point Football Teaser):**
  * `(Teaser 6pt NFL) Kansas City Chiefs -2.5 / (Teaser 6pt NFL) Philadelphia Eagles +8.5`

#### **`Future`**

* **Format:** `Award or Event: Selection`
* **Example:** `Super Bowl LIX Winner: Kansas City Chiefs`

### **5. Master Example Table**

The following table demonstrates the correct formatting for a wide variety of picks, including the new error-handling and parlay rules.

| league | type | pick_value | odds_american |
| :---- | :---- | :---- | ----: |
| `NFL` | Spread | `Kansas City Chiefs -6.5` | -110 |
| `NBA` | Moneyline | `Los Angeles Lakers ML` | 135 |
| `NBA` | Player Prop | `Nikola Jokic: Pts+Reb+Ast Over 50.5` | -115 |
| `NFL` | Period | `1H KC vs PHI Total Over 24` | -110 |
| `NCAAB` | Period | `1H George Mason -6` | -110 |
| `NFL` | Future | `NFC Champion: San Francisco 49ers` | 250 |
| `Other` | Parlay | `(NFL) Cowboys -10.5 / (NBA) Lakers ML` | 264 |
| `NCAAB` | Parlay | `(NCAAB) Nebraska ML / (NCAAB) Drake ML` | 122 |
| `NBA` | Teaser | `(Teaser 4pt NBA) Celtics -3.5 / (Teaser 4pt NBA) Nuggets +5.5` | -120 |
| `Other` | **`Unknown`** | `Tigers First Score Prop` | 150 |
| `NCAAB` | Total | `Rutgers vs Unknown Under 143.5` | -110 |
| `TENNIS` | Moneyline | `Tommy Paul ML` | -150 |
| `TENNIS` | Spread | `Giron +1.5 sets` | -110 |
| `TENNIS` | Spread | `Mpetshi S1 +1.5 games` | -120 |
| `TENNIS` | Total | `Paul vs Rune Over 22.5 games` | -115 |


---

## GRADING RUBRIC

Grade each dimension from 1-10 based on compliance with the specification above.

### 1. EXTRACTION ACCURACY (1-10)
- Did the parser find **ALL** picks in the messages? (Check for missed parlays, split plays, listed picks)
- Were any picks missed completely?
- Were any non-picks incorrectly extracted (false positives - promos, recaps, noise)?
- **Critical:** Each message's picks must be attributed to the correct `message_id`

### 2. PICK FORMATTING (1-10)
Grade against the **exact formats** in the specification:
- **Moneyline:** `Team Name ML` (e.g., "Los Angeles Lakers ML")
- **Spread:** `Team Name +/-X.X` (e.g., "Green Bay Packers -7.5")
- **Total:** `Team A vs Team B Over/Under X` (NOT "Team A/Team B" or "Team A & Team B")
- **Player Prop:** `Player Name: Stat Over/Under X` (e.g., "LeBron James: Pts Over 25.5")
- **Team Prop:** `Team Name: Stat Over/Under X`
- **Period:** `1H/1Q/F5 [Standard Format]` (e.g., "1H NYK vs BOS Total Over 110.5")
- **Parlay:** `(LEAGUE) Leg1 / (LEAGUE) Leg2` - League prefix is **MANDATORY**
- **Tennis:** Special formats per spec (sets, games, ML)
- **Future:** `Award or Event: Selection`

**Deductions for:**
- Using "/" instead of "vs" for totals
- Missing league prefixes on parlay legs
- Using "U" instead of "Under", "O" instead of "Over"
- Player props without colon format
- Odds or units embedded in pick string

### 3. CLASSIFICATION ACCURACY (1-10)
- Is `league` using official abbreviations? (NFL, NCAAB, etc. - see spec)
- Is `type` correct per specification?
  - **Critical:** "Team -7" = Spread, NOT Moneyline
  - **Critical:** "First Half"/"1H" picks = Period, NOT Spread
  - **Critical:** Multi-leg = Parlay, even if same league
  - Tennis set/game spreads = Spread (not Moneyline)
- Cross-league parlays should have `league: "Other"`

### 4. CAPPER ATTRIBUTION (1-10)
- Is `capper_name` the actual tipster, NOT the channel name?
- Are watermarks (@cappersfree, @vippicks) excluded?
- Are different cappers in the same message distinguished?
- Is capper name properly capitalized (not all caps)?

### 5. ODDS & UNITS EXTRACTION (1-10)
- Are American odds extracted correctly (-110, +150)?
- Are odds stored as integers in `odds` field, NOT in pick string?
- Are units parsed correctly (2u → 2.0, "80K" → 80000)?
- Default units = 1.0 when not specified

### 6. DATA COMPLETENESS (1-10)
- **Spreads:** Is `line` populated with the spread value?
- **Props:** Is `subject` (player/team name) and `market` (stat type) populated?
- **Props:** Is `prop_side` set to "Over" or "Under"?
- **Totals:** Is the total number captured in `line`?
- Are all required fields present (message_id, capper_name, league, type, pick)?

---

## RAW INPUT DATA (Source Messages)

Below are the original Telegram messages that were processed:

### MESSAGE 1 (ID: 31597)
**Channel:** Telegram
**Date:** 2026-01-23 19:01 ET
**Caption/Text:**
```
Vezino 

POD 
Milwaukee Bucks -8.5 

Top Opinion!!
Brooklyn nets +8.5
```

### MESSAGE 2 (ID: 31596)
**Channel:** Telegram
**Date:** 2026-01-23 18:44 ET
**Caption/Text:**
```
Tbsportsbetting

Suns - 3 (NBA) 🐋 
Pelicans +6 (NBA)
Indiana -7 (NCAAB)
Tulane +3.5 (NAAB)
```

---

## SCRAPER OUTPUT (Extracted Picks)

Below are the picks extracted by the AI parser:

### PICK 1
- **Message ID:** 31597
- **Capper:** Vezino
- **League:** NBA
- **Type:** Spread
- **Pick:** Milwaukee Bucks -8.5
- **Odds:** N/A
- **Units:** 1.0
- **Subject:** N/A
- **Market:** N/A
- **Line:** -8.5
- **Side:** N/A
- **Result:** Loss

### PICK 2
- **Message ID:** 31597
- **Capper:** Vezino
- **League:** NBA
- **Type:** Spread
- **Pick:** Brooklyn Nets +8.5
- **Odds:** N/A
- **Units:** 1.0
- **Subject:** N/A
- **Market:** N/A
- **Line:** 8.5
- **Side:** N/A
- **Result:** Win

### PICK 3
- **Message ID:** 31596
- **Capper:** Text
- **League:** NBA
- **Type:** Spread
- **Pick:** Tb Suns -3
- **Odds:** N/A
- **Units:** 1.0
- **Subject:** N/A
- **Market:** N/A
- **Line:** -3.0
- **Side:** N/A
- **Result:** Loss

### PICK 4
- **Message ID:** 31596
- **Capper:** Text
- **League:** NBA
- **Type:** Spread
- **Pick:** Pelicans +6
- **Odds:** N/A
- **Units:** 1.0
- **Subject:** N/A
- **Market:** N/A
- **Line:** 6.0
- **Side:** N/A
- **Result:** Win

### PICK 5
- **Message ID:** 31596
- **Capper:** Text
- **League:** NCAAB
- **Type:** Spread
- **Pick:** Indiana -7
- **Odds:** N/A
- **Units:** 1.0
- **Subject:** N/A
- **Market:** N/A
- **Line:** -7.0
- **Side:** N/A
- **Result:** Win

### PICK 6
- **Message ID:** 31596
- **Capper:** Text
- **League:** NCAAB
- **Type:** Spread
- **Pick:** Tulane +3.5
- **Odds:** N/A
- **Units:** 1.0
- **Subject:** N/A
- **Market:** N/A
- **Line:** 3.5
- **Side:** N/A
- **Result:** Win

---

## YOUR EVALUATION

Provide a thorough evaluation following this exact structure:

### DIMENSION SCORES

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| 1. Extraction Accuracy | /10 | |
| 2. Pick Formatting | /10 | |
| 3. Classification Accuracy | /10 | |
| 4. Capper Attribution | /10 | |
| 5. Odds & Units Extraction | /10 | |
| 6. Data Completeness | /10 | |
| **OVERALL** | **/60** | |

---

### MISSED PICKS

List every pick in the raw messages that was NOT extracted. For each:
- **Message ID:** [ID]
- **Missed Pick:** [What the pick says in the source]
- **Expected Output:** [Correct formatted pick per specification]

---

### FALSE POSITIVES / HALLUCINATIONS

List any extracted "picks" that:
1. Are NOT actual betting picks (promos, recaps, commentary)
2. Have incorrect `message_id` (pick attributed to wrong message)
3. Were hallucinated (content from one message appearing in another)

For each:
- **Pick #:** [Number from extracted picks]
- **Issue:** [False positive / Hallucination / Wrong message_id]
- **Details:** [Explanation]

---

### CLASSIFICATION ERRORS

List picks with wrong `type` or `league`. For each:
- **Pick #:** [Number]
- **Current:** type="{current_type}", league="{current_league}"
- **Correct:** type="{correct_type}", league="{correct_league}"
- **Reason:** [Why this is wrong per specification]

**Pay special attention to:**
- Spreads misclassified as Moneyline (e.g., "Team -7" should be Spread)
- Period bets not marked as type="Period"
- Parlays not marked as type="Parlay"

---

### FORMATTING ERRORS

List picks that don't match the specification format. For each:
- **Pick #:** [Number]
- **Current Format:** [What was extracted]
- **Correct Format:** [What it should be per specification]
- **Rule Violated:** [Which formatting rule from the spec]

**Common violations to check:**
- Totals using "/" instead of "vs"
- Player props missing colon format
- Parlays missing (LEAGUE) prefix on each leg
- Over/Under abbreviated as O/U
- Odds embedded in pick string

---

### STRUCTURED FIELD ERRORS

List picks missing required structured fields:
- **Spreads:** Missing `line` field
- **Props:** Missing `subject`, `market`, or `prop_side`
- **Totals:** Missing `line` or `prop_side`

---

### SUMMARY

Provide a 3-5 sentence summary covering:
1. Overall performance assessment
2. The single most critical issue to fix
3. Pattern of errors (if any)
4. Recommended priority for fixes
