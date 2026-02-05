# Golden Set Generation Instructions

## Overview
We are splitting the benchmark into two stages:
1.  **OCR Benchmark**: Measures text transcription accuracy.
2.  **Parsing Benchmark**: Measures JSON extraction accuracy from text.

## Step 1: Generate the PDF
First, create a PDF containing all the benchmark images.
Run: `python benchmark/tools/generate_pdf.py` (You need to implement this tool if not exists).
*For now, you can just zip the images or upload them to the AI chat.*

## Step 2: Generate "OCR Golden Set" (Ground Truth Text)
**Goal**: Get the *perfect* raw text transcription for each image.

**Prompt for AI (GPT-4o / Claude 3.5 Sonnet)**:
```text
I am creating a Golden Set for OCR benchmarking. 
Attached is a PDF/Zip of 30 sports betting slips/picks.

For each image, I need the EXACT text transcription. 
- Do NOT correct spelling errors (unless it's obviously a glitch).
- Maintain line breaks.
- Ignore decorative elements or logos.
- **CRITICAL**: Do NOT transcribe the red watermark text "@cappersfree" or similar promotional overlays. We want the cleaner version.
- Output the result as a JSON object where keys are the image filenames and values are the raw text strings.

Format:
{
  "image_01.jpg": "BET ID: 12345\nLeg 1: Lakers -5...",
  "image_02.jpg": "..."
}
```

## Step 3: Generate "Parsing Golden Set" (Ground Truth JSON)
**Goal**: Get the *perfect* structured JSON pick data for each image.

**Prompt for AI**:
```text
I am creating a Golden Set for Sports Betting Parser benchmarking.
Below is the raw text for 30 betting slips (provided in the previous step).

For each text entry, extract the betting picks into the following JSON schema (Production Format).

### **CRITICAL INSTRUCTIONS**
1.  **Odds:** Extract American odds (e.g., -110). If NOT visible, set "od": null. DO NOT GUESS.
2.  **Multiple Cappers:** Separate into distinct objects.

### **Sports Pick Data Formatting Guide**

### **1. Standardized `league` Values**
| League | Description |
| :--- | :--- |
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
| `Other` | Multi-sport Parlay (e.g. NBA + NFL) OR Unknown |

### **2. Standardized `type` Values**
| Type | Description |
| :--- | :--- |
| `Moneyline` | Win outright |
| `Spread` | Margin of victory (Point Spread, Run/Puck Line) |
| `Total` | Combined score Over/Under |
| `Player Prop` | Player's statistical performance |
| `Team Prop` | Team's statistical performance (includes Team Totals) |
| `Game Prop` | Game event not tied to final outcome |
| `Period` | Quarter, Half, Period specific bet |
| `Parlay` | Two or more linked wagers |
| `Teaser` | Parlay with adjusted spreads/totals |
| `Future` | Long-term bet on future event |
| `Unknown` | Cannot determine bet type |

### **3. `pick_value` Format by Type**

**Key Rules:**
- The `pick_value` describes WHAT is being bet. Odds (-110) go ONLY in `odds_american`.
- Omit trailing `.0` decimals. Use `48` not `48.0`, but keep `48.5`.
- If type is `Unknown`, use original unformatted text.

#### `Moneyline`
Format: `Team or Competitor Name ML`
Example: `Los Angeles Lakers ML`

#### `Spread`
Format: `Team Name [space] Point Spread`
Example: `Green Bay Packers -7.5`

#### `Total`
Format: `Team A vs Team B Over/Under Number`
Example: `Lakers vs Celtics Over 215.5`, `Rutgers vs Unknown Under 143.5`

#### `Player Prop`
Format: `Player Name: Stat Over/Under/Value`
Example: `LeBron James: Pts Over 25.5`

#### `Team Prop`
Format: `Team Name: Stat Over/Under/Value`
Example: `Dallas Cowboys: Total Points Over 27.5`

#### `Game Prop`
Format: `Description: Value`
Example: `Fight to go the Distance: No`

#### `Period`
Format: `Period Identifier [Standard Bet Format]`
Identifiers: `1H`, `2H`, `1Q`, `2Q`, `3Q`, `4Q`, `P1`, `P2`, `P3`, `F5`, `F3`, `F1`, `Set 1`, `60 min`
Example: `1H NYK vs BOS Total Over 110.5`, `1Q Thunder -2`

#### `Parlay` / `Teaser`
Format: `(League) Leg 1 / (League) Leg 2 / ...`
- Prefix EACH leg with league in parentheses: `(NFL)`, `(NBA)`, etc.
- For Teasers, include points: `(Teaser 6pt NFL)`
Examples:
- `(NFL) Cowboys -10.5 / (NBA) Lakers ML`
- `(Teaser 6pt NFL) Chiefs -2.5 / (Teaser 6pt NFL) Eagles +8.5`

#### `Future`
Format: `Award or Event: Selection`
Example: `Super Bowl LIX Winner: Kansas City Chiefs`

### **REQUIRED OUTPUT FORMAT (JSON OBJECT)** 'picks'
Respond ONLY with a JSON Object with a "picks" key containing the array using SHORT KEYS to save tokens:
- "id": 1 (Sequential ID)
- "cn": capper_name
- "lg": league (Standardized)
- "ty": type
- "p": pick (Formatted according to rules above)
- "od": odds (int or null)
- "u": units (float, default 1.0)
- "dt": date (YYYY-MM-DD)

Output the result as a master JSON object keyed by filename:
{
  "image_01.jpg": [ ... extracted picks data ... ],
  "image_02.jpg": [ ... extracted picks data ... ]
}
```

## Step 4: Save the Files
1.  Save the text output from Step 2 as `benchmark/dataset/ocr_golden_set.json`.
2.  Save the JSON output from Step 3 as `benchmark/dataset/parsing_golden_set.json`.
