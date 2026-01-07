import json
from datetime import datetime
from src.utils import clean_text_for_ai

def get_master_formatting_guide():
    return """
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
Stats: `Pts`, `Reb`, `Ast`, `3PM`, `PRA` (Pts+Reb+Ast), `PassYds`, `RushYds`, `RecYds`, `PassTD`, `Rec`, `Comp`, `K`, `H`, `HR`, `RBI`, `TotalBases`, `SOG`, `G`, `A`, `P`
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
- `(NFL) Jalen Hurts: RushYds Over 48.5 / (NFL) A.J. Brown: RecYds Over 80.5`
- `(Teaser 6pt NFL) Chiefs -2.5 / (Teaser 6pt NFL) Eagles +8.5`

#### `Future`
Format: `Award or Event: Selection`
Example: `Super Bowl LIX Winner: Kansas City Chiefs`
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
        
    full_raw_data = "\\n".join(raw_content_list)
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
- "u": units (float, default 1.0)

Example:
{{
  "picks": [
      {{ "id": 12345, "cn": "KingCap", "lg": "NBA", "ty": "Player Prop", "p": "LeBron James: Pts Over 25.5", "od": -110, "u": 1.0 }}
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
2. **LG (League)**: NFL, NBA, MLB, etc. **IMPORTANT: If Multi-Sport Parlay (e.g. NBA+NFL), MUST use "Other".**
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

def generate_multimodal_prompt(selected_data, image_map):
    """
    Generates a prompt for Multimodal AI (User uploads images + this prompt).
    image_map: { msg_id: ["filename1.jpg", "filename2.jpg"] }
    """
    context_list = []
    
    for item in selected_data:
        mid = item['id']
        caption = clean_text_for_ai(item.get('text', ''))
        filenames = image_map.get(mid, [])
        
        if not filenames:
            # If no images, just provide text
            entry = f"### Message {mid}\\n[No Image]\\n[Context]: {caption}"
            context_list.append(entry)
        else:
            for fname in filenames:
                entry = f"### Image File: {fname}\\n[Message ID]: {mid}\\n[Context]: {caption}"
                context_list.append(entry)
            
    full_context = "\\n\\n".join(context_list)
    current_date = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
*** SYSTEM INSTRUCTION: SET TEMPERATURE TO 0 ***
*** OUTPUT FORMAT: SINGLE LINE RAW JSON ONLY. NO MARKDOWN. ***

You are an expert sports betting data parser. I have uploaded a set of images containing betting picks.
Below is the CAPTION/CONTEXT text associated with each image file.

Use BOTH the image visual data and the provided context text to extract the picks.

### **CRITICAL INSTRUCTIONS**
1.  **Map Picks to correct Message ID**: Use the '[Message ID]' provided in the context for each image.
2.  **Combine Data**: Visuals give you the pick/odds, Context gives you the Capper/Sport often.
3.  **Odds**: Extract American odds (e.g., -110). If NOT visible, set "od": null.
4.  **Multiple Cappers**: If multiple picks in one image, separate them.

### **AVOID THESE COMMON MISTAKES:**
- **MARKETING HEADERS**: "80K MAIN PLAY", "VIP WHALE PLAY", "MAX BET" -> IGNORE.
- **Sportsbook names**: "Hard Rock", "DraftKings" -> IGNORE.
- **Watermarks**: "@cappersfree" is NOT the capper. Look for the real name.

{get_master_formatting_guide()}

### **REQUIRED OUTPUT FORMAT (JSON OBJECT)**
Respond ONLY with a JSON Object with a "picks" key containing the array using SHORT KEYS:
- "id": message_id (FROM CONTEXT)
- "cn": capper_name
- "lg": league
- "ty": type
- "p": pick
- "od": odds (int or null)
- "u": units (float, default 1.0)
- "u": units (float, default 1.0)

Example:
{{
  "picks": [
      {{ "id": 12345, "cn": "KingCap", "lg": "NBA", "ty": "Player Prop", "p": "LeBron James: Pts Over 25.5", "od": -110, "u": 1.0 }}
  ]
}}

### **IMAGE CONTEXT DATA**
{full_context}
"""
    return prompt