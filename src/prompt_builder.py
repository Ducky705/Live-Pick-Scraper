import json
from datetime import datetime
from src.utils import clean_text_for_ai

def get_master_formatting_guide():
    return """
### **Sports Pick Data Formatting Guide**

### **1. Introduction**
This document specifies the standard format for storing sports betting picks. Adherence to this guide is mandatory.

### **2. Standardized `league` Column Values**
Use the following official uppercase abbreviations for the `league` column. 

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
| `SOCCER` | All Soccer Leagues (EPL, La Liga, MLS, etc.) |
| `EUROLEAGUE` | EuroLeague Basketball |
| `PGA` | PGA Tour |
| `F1` | Formula 1 |
| `Other` | Parlay with multiple leagues OR Unknown |

### **3. Standardized `type` Column Values**
The `type` column must use one of the following values:

| Type | Description |
| :--- | :--- |
| `Moneyline` | Win outright. |
| `Spread` | Margin of victory (e.g. -7.5). |
| `Total` | Over/Under combined score. |
| `Player Prop` | Specific player's performance. |
| `Team Prop` | Specific team's performance. |
| `Game Prop` | Event not tied to final outcome. |
| `Period` | Quarter, Half, Period, Set. |
| `Parlay` | Linked wagers. |
| `Teaser` | Adjusted spreads/totals. |
| `Future` | Long-term event. |
| `Unknown` | Cannot determine. |

### **4. `pick_value` Format Specification**
The format of the `pick_value` string is strictly determined by the bet `type`.

**Key Rules:**
*   **Pick vs. Odds:** The `pick_value` describes *what* is being bet on. Payouts (e.g. -110) go to `odds_american`.
*   **Decimals:** Omit trailing .0 (use `48` not `48.0`). Retain necessary decimals (`48.5`).
*   **Unknown Type:** Use original unformatted text.

#### **`Moneyline`**
*   `Team or Competitor Name ML`
*   Example: `Los Angeles Lakers ML`

#### **`Spread`**
*   `Team Name [space] Point Spread`
*   Example: `Green Bay Packers -7.5`

#### **`Total`**
*   `Team A vs Team B Over/Under Number`
*   Example: `Lakers vs Celtics Over 215.5`

#### **`Player Prop`**
*   `Player Name: Stat Over/Under/Value`
*   Stats: `Pts`, `Reb`, `Ast`, `PRA`, `PassYds`, `RushYds`, `RecYds`, `PassTD`, `Rec`, `K`, `H`, `HR`, `RBI`, `SOG`, `G`, `A`.
*   Example: `LeBron James: Pts Over 25.5`

#### **`Team Prop`**
*   `Team Name: Stat Over/Under/Value`
*   Example: `Dallas Cowboys: Total Points Over 27.5`

#### **`Game Prop`**
*   `Description: Value`
*   Example: `Fight to go the Distance: No`

#### **`Period`**
*   `Period Identifier [Standard Bet Format]`
*   Ids: `1H`, `2H`, `1Q`, `2Q`, `3Q`, `4Q`, `P1`, `P2`, `P3`, `F5`.
*   Example: `1H NYK vs BOS Total Over 110.5`

#### **`Parlay` / `Teaser`**
*   `(League) Leg 1 / (League) Leg 2`
*   Prefix each leg with league in parens.
*   Example: `(NFL) Cowboys -10.5 / (NBA) Lakers ML`
*   Teaser: `(Teaser 6pt NFL) Chiefs -2.5 / (Teaser 6pt NFL) Eagles +8.5`

#### **`Future`**
*   `Award or Event: Selection`
*   Example: `Super Bowl LIX Winner: Kansas City Chiefs`
"""


def generate_ai_prompt(selected_data):
    # COMPRESSED INPUT FORMAT
    raw_content_list = []
    for item in selected_data:
        entry = f"### {item['id']}"
        
        text_content = clean_text_for_ai(item.get('text', ''))
        ocr_texts = item.get('ocr_texts', [])
        
        # Fallback to legacy field if new list is empty but old field exists
        if not ocr_texts and item.get('ocr_text'):
             ocr_texts = [item.get('ocr_text')]

        if text_content:
            entry += f" [T] {text_content}"
        
        if ocr_texts:
            for i, ocr_block in enumerate(ocr_texts):
                cleaned_ocr = clean_text_for_ai(ocr_block)
                if cleaned_ocr:
                    entry += f" [OCR {i+1}] {cleaned_ocr}"
            
        raw_content_list.append(entry)
        
    full_raw_data = "\n".join(raw_content_list)
    current_date = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
*** SYSTEM INSTRUCTION: SET TEMPERATURE TO 0 ***
*** OUTPUT FORMAT: SINGLE LINE RAW JSON ONLY. NO MARKDOWN. ***

You are an expert sports betting data parser. Extract betting picks.

### **CRITICAL INSTRUCTIONS**
1.  **Capper:** Look in [T] (Text) first, then [O] (OCR).
2.  **Odds:** Extract American odds (e.g., -110). If NOT visible, set "od": null. DO NOT GUESS.
3.  **Multiple Cappers:** Separate into distinct objects.

### **AVOID THESE COMMON MISTAKES:**
These are NOT valid picks - format them correctly or skip:
- **MARKETING HEADERS**: "80K MAIN PLAY", "VIP WHALE PLAY", "MAX BET", "LOCK OF THE CENTURY". These are titles, NOT picks.
- **Record labels**: "5-2 Run", "Last 10: 8-2".
- **Sportsbook names**: "Hard Rock", "DraftKings" → These are where to bet, not what to bet.
- **Generic descriptions**: "Player Passing Yards O/U" → Include the player name AND number.

- **Generic descriptions**: "Player Passing Yards O/U" → Include the player name AND number.

**IF A TEXT SAYS "80K MAIN PLAY" or "VIP", IGNORE IT UNLESS THERE IS A TEAM AND LINE.**
- "80K" = UNITS (u: 80000). It is NOT the pick.
- Example Invalid: {{"p": "80K MAIN PLAY"}} -> REJECT
- Example Valid: "80K MAIN PLAY: Lakers -5" -> {{"p": "Lakers -5", "u": 80000}}

A properly formatted pick contains:
- A specific team name OR player name (e.g. "Lakers", "LeBron James", "Chiefs")
- AND a specific number or "ML" (e.g. "-7.5", "Over 215.5", "ML")

### **WATERMARKS ARE NOT CAPPERS!**
These are CHANNEL WATERMARKS, not capper names. NEVER use these as "cn":
- "@cappersfree", "cappersfree", "capperstree", "@freepicks", "@vippicks"  
- "WHALE PLAYS", "SU", "Card", "POTD", "LOCK", "FREE PLAY"
The REAL capper name is a person/brand name that appears BEFORE/ABOVE the watermark.
Example: "3 LEARLOCKS @cappersfree" = cn is "3 Learlocks" (NOT "cappersfree")
Example: "HammeringHank CFB" = cn is "HammeringHank"

{get_master_formatting_guide()}

### **REQUIRED OUTPUT FORMAT (JSON OBJECT)**
Respond ONLY with a JSON Object with a "picks" key containing the array using SHORT KEYS to save tokens:
- "id": message_id
- "cn": capper_name
- "lg": league (Standardized)
- "ty": type
- "p": pick
- "od": odds (int or null)
- "u": units (float, default 1.0)
- "dt": date (YYYY-MM-DD)

Example:
{{
  "picks": [
      {{ "id": 12345, "cn": "KingCap", "lg": "NBA", "ty": "Player Prop", "p": "LeBron James: Pts Over 25.5", "od": -110, "u": 1.0, "dt": "{current_date}" }}
  ]
}}

### **RAW DATA**
{full_raw_data}
"""
    return prompt

def generate_revision_prompt(failed_items):
    """
    Generates a targeted refinement prompt using MINIFIED keys.
    """
    items_detail = []
    for item in failed_items:
        # Minify keys for input
        detail = {
            "id": item.get("message_id"),
            "fails": [],
            "vals": {},
            "ctx": clean_text_for_ai(item.get("original_text", ""))[:800]
        }
        
        # Identify specifically what's wrong
        if item.get("capper_name") in ["Unknown", "N/A", None, ""]:
            detail["fails"].append("cn")
            detail["vals"]["cn"] = "Unknown"
        if item.get("league") in ["Unknown", "Other", None, ""]:
            detail["fails"].append("lg")
            detail["vals"]["lg"] = item.get("league", "Unknown")
        if not item.get("pick") or item.get("pick") == "Unknown" or True: 
            detail["fails"].append("p")
            detail["vals"]["p"] = item.get("pick", "Unknown")
            
        items_detail.append(detail)
    
    items_json = json.dumps(items_detail, indent=None, separators=(',', ':')) # Minified JSON
    
    return f"""
*** SYSTEM INSTRUCTION: SET TEMPERATURE TO 0.1 ***
*** OUTPUT FORMAT: RAW JSON ONLY (Minified keys). ***

### REFINEMENT TASK
Re-analyze failed fields using the Context (ctx).

### TIPS
1. **CN (Capper)**: Look at top of image/text.
2. **LG (League)**: NFL, NBA, MLB, etc.
3. **P (Pick)**: "Team -7.5", "Team ML".

### NOISE CORRECTION
If "pick" has "80K", "VIP", "MAX BET" -> IGNORE. Find the REAL bet. If none, return "p": null.

### INPUT DATA
{items_json}

### OUTPUT FORMAT
JSON Array of objects with ONLY fixed fields using SHORT KEYS:
- "id": (same as input)
- "cn": capper_name
- "lg": league
- "p": pick

Example:
[{{ "id": 123, "cn": "TheRealCapper", "lg": "NBA" }}]
"""

def generate_smart_fill_prompt(unknown_items):
    # Minified Input
    minified = []
    for item in unknown_items:
        minified.append({
            "id": item.get("message_id"),
            "p": item.get("pick"),
            "ctx": clean_text_for_ai(item.get("context", ""))
        })
        
    items_json = json.dumps(minified, separators=(',', ':'))
    
    return f"""
*** SYSTEM INSTRUCTION: SET TEMPERATURE TO 0.1 ***
*** OUTPUT FORMAT: RAW JSON ONLY. ***

Identify "cn" (Capper Name).

INPUT:
{items_json}

OUTPUT (JSON Array):
[ {{ "id": 123, "cn": "FoundName" }} ]
"""
generate_compact_prompt = generate_ai_prompt
