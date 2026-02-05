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
