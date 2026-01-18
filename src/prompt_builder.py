import json
from datetime import datetime
from src.utils import clean_text_for_ai
from src.album_correlator import generate_album_context, AlbumCorrelator

def get_master_formatting_guide():
    return """
### **Sports Pick Data Formatting Guide**

### **1. Standardized `league` Column Values**
Use the following official uppercase abbreviations for the `league` column.

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

### **2. Standardized `type` Column Values**
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

### **3. `pick_value` Format Specification**

**Key Formatting Rules:**
* **Pick vs. Odds:** The `pick_value` string describes *what* is being bet on. The price/payout (e.g., -110, +150) must **only** be stored in the `odds` column. NEVER include odds in the pick!
* **Number Formatting:** For all numerical values, omit trailing `.0` decimals. Use `48` instead of `48.0`, but retain decimals where necessary (e.g., `48.5`).
* **Unknown Type Handling:** If the `type` is set to `Unknown`, the `pick_value` column must contain the **original, unformatted text** of the pick.

#### `Moneyline`
* **Format:** `Team or Competitor Name ML`
* **Example:** `Los Angeles Lakers ML`

#### `Spread`
* **Format:** `Team Name [space] Point Spread`
* **Example:** `Green Bay Packers -7.5`

#### `Total`
* **Format:** `Team A vs Team B Over/Under Number`
* **Note:** The matchup `Team A vs Team B` is required context. The team on the right is typically the home team. If one team is unknown, use "Unknown".
* **Example:** `Lakers vs Celtics Over 215.5`, `Rutgers vs Unknown Under 143.5`

#### `Player Prop`
* **Format:** `Player Name: Stat Over/Under Value`
* **Standard Stat Abbreviations:**
  * **Basketball:** `Pts`, `Reb`, `Ast`, `Blk`, `Stl`, `3PM`, `Pts+Reb+Ast` (or `PRA`)
  * **Football:** `PassYds`, `RushYds`, `RecYds`, `PassTD`, `Rec`, `Comp`
  * **Baseball:** `K`, `H`, `HR`, `RBI`, `TotalBases`
  * **Hockey:** `SOG`, `G`, `A`, `P`
* **Example:** `LeBron James: Pts Over 25.5`

#### `Team Prop`
* **Format:** `Team Name: Stat Over/Under Value`
* **Example:** `Dallas Cowboys: Total Points Over 27.5`

#### `Game Prop`
* **Format:** `Description of Prop: Value`
* **Example:** `Fight to go the Distance: No`

#### `Period`
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

#### `Tennis` (TENNIS League - Special Rules)
Tennis picks use different formats than team sports:
* **Moneyline:** `Player Name ML` - Example: `Tommy Paul ML`, `Sinner ML`
* **Set Spread:** `Player Name +/-X.X sets` - Example: `Giron +1.5 sets`, `Paul -1.5 sets`
* **Game Spread (Match):** `Player Name +/-X.X games` - Example: `Rune +3.5 games`
* **Game Spread (Set):** `Player Name Set X +/-X.X games` - Example: `Mpetshi S1 +1.5 games`
* **Total Games:** `Player A vs Player B Over/Under X.X games` - Example: `Paul vs Rune Over 22.5 games`
* **Set Winner:** `Player Name to win Set X` - Example: `Sinner to win Set 1`

#### `Parlay` / `Teaser`
* **Format:** `(Leg 1 League) Details / (Leg 2 League) Details / ...`
* **Rule:** Each leg is described using its standard format (e.g., `Team -X.5`, `Team ML`) and separated by ` / `. The bet type (Spread, ML, etc.) is **not** included in the leg description.
* **League Prefix:** Prefixing each leg with its league in parentheses (e.g., `(NFL)`) is **mandatory**.
* **Teasers:** For Teasers, include the teaser points and the league: `(Teaser 6pt NFL) ...`
* **Parlay Examples:**
  * `(NFL) Dallas Cowboys -10.5 / (NFL) San Francisco 49ers ML`
  * `(NFL) Jalen Hurts: RushYds Over 48.5 / (NFL) A.J. Brown: RecYds Over 80.5`
  * `(NFL) Cowboys -10.5 / (NBA) Lakers ML`
* **Teaser Example:** `(Teaser 6pt NFL) Kansas City Chiefs -2.5 / (Teaser 6pt NFL) Philadelphia Eagles +8.5`

#### `Future`
* **Format:** `Award or Event: Selection`
* **Example:** `Super Bowl LIX Winner: Kansas City Chiefs`

### **4. Master Example Table**
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
| `Other` | Unknown | `Tigers First Score Prop` | 150 |
| `NCAAB` | Total | `Rutgers vs Unknown Under 143.5` | -110 |
| `TENNIS` | Moneyline | `Tommy Paul ML` | -150 |
| `TENNIS` | Spread | `Giron +1.5 sets` | -110 |
| `TENNIS` | Spread | `Mpetshi S1 +1.5 games` | -120 |
| `TENNIS` | Total | `Paul vs Rune Over 22.5 games` | -115 |
"""


def generate_ai_prompt(selected_data):
    # COMPRESSED INPUT FORMAT
    raw_content_list = []
    album_contexts = []  # Store album correlation contexts
    
    for item in selected_data:
        entry = f"### {item['id']}"
        
        text_content = clean_text_for_ai(item.get('text', ''))
        ocr_texts = item.get('ocr_texts', [])
        image_paths = item.get('images', [])
        
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
        
        # Generate album correlation context if this is a multi-image post
        if len(image_paths) > 1 and len(ocr_texts) > 1:
            album_ctx = generate_album_context(
                caption=text_content,
                ocr_texts=ocr_texts,
                image_paths=image_paths,
                channel_name=item.get('channel_name')
            )
            if album_ctx:
                album_contexts.append(f"**Message {item['id']}:**\n{album_ctx}")
            
        raw_content_list.append(entry)
        
    full_raw_data = "\\n".join(raw_content_list)
    
    # Build album correlation section if any albums detected
    album_section = ""
    if album_contexts:
        album_section = """
### **ALBUM IMAGE-TO-CAPPER MAPPING (CRITICAL!)**
The following messages contain MULTIPLE IMAGES with capper names listed in the caption.
USE THIS MAPPING to correctly attribute picks to cappers.

""" + "\n\n".join(album_contexts) + "\n"

    prompt = f"""
*** SYSTEM INSTRUCTION: SET TEMPERATURE TO 0 ***
*** OUTPUT FORMAT: SINGLE LINE RAW JSON ONLY. NO MARKDOWN. ***

You are an expert sports betting data parser. Extract ALL betting picks from ALL messages.

### **CRITICAL INSTRUCTIONS**
1.  **CONFLICT RESOLUTION (MANDATORY):**
    - If the Text/Header says "ML" but the Ticket/Image says "PK" or "Pick'em", **YOU MUST OUTPUT 'Spread' and '+0'**.
    - **Trust the Ticket** over the Capper's typed text.
    - Example: Text "Marquette ML", Ticket "Marquette PK". -> Result: "Marquette +0" (Spread).
2.  **Capper:** Look in [T] (Text) first, then [O] (OCR).
2.  **Odds MUST be SEPARATE from Pick:** 
    - Extract American odds (e.g., -110, +150) into the \"od\" field ONLY.
    - The \"p\" field must NOT contain odds - only the team/player and line.
    - Example: \"Lakers -5 -110\" → \"p\": \"Lakers -5\", \"od\": -110
    - Example: \"Chiefs ML +155\" → \"p\": \"Chiefs ML\", \"od\": 155
    - If odds are NOT visible, set \"od\": null. DO NOT GUESS.
3.  **Fragmented OCR:** OCR text may be split. Reconstruct context.
    - "Lakers" (line 1) + "-5" (line 2) -> Pick: "Lakers -5"
    - "NBA" (line 1) + "Celtics ML" (line 2) -> League: "NBA", Pick: "Celtics ML"
    - Ignore isolated noise like "17:31", "5G", "LTE".

### **FORBIDDEN PHRASES (NEGATIVE CONSTRAINTS)**
- **NEVER** output "DM for picks" or "DM @cappersfree" as a pick. If no pick is found, output nothing for that message.
- **NEVER** output marketing text like "Join the VIP", "Click Here", "Promo".
- **NEVER** output "Unknown" as a pick text.

### **MULTI-CAPPER DETECTION (CRITICAL!)**
**SITUATION:** A single image/message may show picks from MULTIPLE DIFFERENT CAPPERS (e.g., a screenshot mosaic or merged images).
**DETECTION SIGNALS:**
- Different usernames/headers (e.g., "A11Bets" section and "HammeringHank" section)
- Visual separations (lines, borders, background color changes)
- Different formatting styles or emoji usage
- Different profile pictures or avatars

**REQUIRED ACTION:**
1. **DO NOT MERGE** picks from different cappers into one entry
2. Each capper's picks get their OWN SEPARATE entries with their OWN "cn" field
3. If "A11Bets" has 3 picks and "HammeringHank" has 2 picks in ONE image, output 5 SEPARATE pick objects:
   - 3 objects with "cn": "A11Bets"
   - 2 objects with "cn": "HammeringHank"
4. **DO NOT** output a comma-separated list of names in "cn" (e.g., "A11Bets, TTW" is INVALID). Pick ONE name per object.

**EXAMPLE:**
Image shows: "[A11Bets] Eagles ML, Lakers -5" ... "[HammeringHank] Chiefs +3"
OUTPUT:
```
[
  {{"id": 123, "cn": "A11Bets", "p": "Eagles ML", ...}},
  {{"id": 123, "cn": "A11Bets", "p": "Lakers -5", ...}},
  {{"id": 123, "cn": "HammeringHank", "p": "Chiefs +3", ...}}
]
```

### **AVOID THESE COMMON MISTAKES:**
These are NOT valid picks - format them correctly or skip:
- **MARKETING HEADERS**: "80K MAIN PLAY", "VIP WHALE PLAY", "MAX BET", "LOCK OF THE CENTURY". These are titles, NOT picks.
- **Record labels**: "5-2 Run", "Last 10: 8-2".
- **Sportsbook names**: "Hard Rock", "DraftKings" → These are where to bet, not what to bet.
- **Generic descriptions**: "Player Passing Yards O/U" → Include the player name AND number.

### **BANKROLL ADVICE IS NOT A PICK - SKIP THESE:**
These are betting strategy suggestions, NOT actual picks. DO NOT extract these:
- "Whale play = 4%", "Straight bet = 2%", "Max bet = 5%"
- "Bankroll management", "Unit sizing", "Bet 2% of bankroll"
- "Risk 1u to win 2u", "Flat betting strategy"
- Any text that talks about percentages of bankroll or betting strategy without a specific team/player

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

### **5. Conflict Resolution & Special Cases**
* **Ticket vs. Commentary:** If the capper's text/header says one thing (e.g., "Team ML") but the actual Ticket/Screenshot says another (e.g., "Team PK" or "Team +0"), **TRUST THE TICKET**.
  * Example: Header "Marquette ML", Ticket "MARQUETTE PK-110". Result: "Marquette +0" (Spread).
* **PK / Pick'em:** Treat "PK", "Pick", or "Pick'em" as Spread `+0` (or `+0.0`).
  * Example: "Lakers PK" -> "Lakers +0" (Type: Spread).
* **Conflicting Odds:** If text says "-110" and ticket says "-115", trust the ticket.

### **6. SHORT NAME / ABBREVIATION DETECTION**
* **Initials are Cappers**: If a caption starts with 2-4 Uppercase Letters followed by a play type or parentheses (e.g., "**BL (Diamond Play)**", "KOF Whale", "JMO"), the Initials ARE the Capper Name.
  * Example: "**BL (Diamond Play)**" -> cn: "BL" (NOT Unknown)
  * Example: "KOF 100k" -> cn: "KOF"
  * Example: "SB - " -> cn: "SB"

{get_master_formatting_guide()}

### **REQUIRED OUTPUT FORMAT (JSON OBJECT)**
Respond ONLY with a JSON Object with a \"picks\" key containing the array using SHORT KEYS to save tokens:
- \"id\": message_id
- \"cn\": capper_name
- \"lg\": league (Standardized)
- \"ty\": type
- \"p\": pick (NO ODDS HERE! Just team/player and line)
- \"od\": odds (int or null - THIS is where odds go!)
- \"u\": units (float, default 1.0)

**CORRECT Example (odds separated):**
{{
  \"picks\": [
      {{ \"id\": 12345, \"cn\": \"KingCap\", \"lg\": \"NBA\", \"ty\": \"Spread\", \"p\": \"Lakers -5\", \"od\": -110, \"u\": 1.0 }},
      {{ \"id\": 12346, \"cn\": \"BetMaster\", \"lg\": \"NFL\", \"ty\": \"Moneyline\", \"p\": \"Chiefs ML\", \"od\": 155, \"u\": 2.0 }},
      {{ \"id\": 12347, \"cn\": \"PropKing\", \"lg\": \"NBA\", \"ty\": \"Player Prop\", \"p\": \"LeBron James: Pts Over 25.5\", \"od\": -115, \"u\": 1.0 }}
  ]
}}

**WRONG Example (DO NOT DO THIS - odds in pick!):**
{{ \\\"p\\\": \\\"Lakers -5 -110\\\" }} ← WRONG! Odds should be in \\\"od\\\" field!

{album_section}
### **RAW DATA**
{full_raw_data}
"""
    return prompt

def generate_revision_prompt(failed_items, reference_picks=None):
    """
    Generates a "Super Useful" targeted refinement prompt using MINIFIED keys.
    """
    items_detail = []
    for item in failed_items:
        # Minify keys for input
        detail = {
            "id": item.get("message_id"),
            "fails": [],
            "vals": {
                "cn": item.get("capper_name", "Unknown"),
                "lg": item.get("league", "Unknown"),
                "ty": item.get("type", "Unknown"),
                "p": item.get("pick", "Unknown")
            },
            "ctx": clean_text_for_ai(item.get("original_text", ""))[:800]
        }
        
        # Identify specifically what's wrong (for context, though AI should just fix all)
        if item.get("capper_name") in ["Unknown", "N/A", None, ""]:
            detail["fails"].append("cn")
        if item.get("league") in ["Unknown", "Other", None, ""]:
            detail["fails"].append("lg")
        if not item.get("pick") or item.get("pick") == "Unknown": 
            detail["fails"].append("p")
            
        items_detail.append(detail)
    
    items_json = json.dumps(items_detail, indent=None, separators=(',', ':')) # Minified JSON
    
    # Process Reference Picks (Minified)
    ref_json = "[]"
    if reference_picks:
        minified_refs = []
        for rp in reference_picks[:50]: # Limit context
             minified_refs.append({
                 "p": rp.get('pick'),
                 "o": rp.get('odds'),
                 "lg": rp.get('league')
             })
        ref_json = json.dumps(minified_refs, indent=None, separators=(',', ':'))

    return f"""
*** SYSTEM INSTRUCTION: SET TEMPERATURE TO 0 ***
*** OUTPUT FORMAT: RAW JSON ARRAY ONLY. ***

### TASKS: FIX MISSING OR INCORRECT DATA
You are a Sports Betting Expert Inspector. Your goal is absolute accuracy.

### 1. INTELLIGENT PARLAY DETECTION
- If pick text has multiple events ("/" or " + "), it is a **PARLAY**.
- **CRITICAL LEAGUE RULE FOR PARLAYS**: 
    - Same Sport (e.g. NBA+NBA) -> `lg`="NBA".
    - **Multi-Sport (e.g. NCAAF+NCAAB, NFL+NBA) -> `lg`="Other" (ABSOLUTE RULE)**.
    - **NEVER OUTPUT**: "NCAAF/NCAAB", "NFL/NBA", "Mixed", or any combined league string.
    - **DO NOT CHANGE "Other" TO "Mixed"** - "Mixed" is NOT a valid league value!
    - **DO NOT CHANGE "Other" TO ANYTHING ELSE FOR MULTI-SPORT PARLAYS**.
- **Anti-Hallucination**:
    - "Other" is a VALID league. Do not force a guess.
    - International Basketball is NOT Soccer.

### 1B. FORBIDDEN CHANGES (DO NOT MAKE THESE!)
**LEAGUE ERRORS TO AVOID:**
- ❌ DO NOT change "Other" to "Mixed" (Mixed is invalid!)
- ❌ DO NOT change "Other" to "Parlay" (Parlay is a type, not a league!)
- ❌ DO NOT create combined leagues like "NFL/NBA" or "NCAAF/NCAAB"

**TYPE ERRORS TO AVOID:**
- ❌ DO NOT change "Team Prop" to "Prop" (Team Prop is MORE specific and correct!)
- ❌ DO NOT change "Player Prop" to "Prop" (Player Prop is MORE specific and correct!)
- ✅ Valid types: Moneyline, Spread, Total, Player Prop, Team Prop, Parlay, Teaser, Period, Futures

### 2. REFERENCE MATCHING (CROSS-FILL ODDS)
- Check the **REFERENCE SHEET** below.
- If a failed pick matches a Reference Pick semantically (e.g. "Joker Over" matches "Nikola Jokic Over 28.5"), **FILL THE ODDS** from the reference.
- **Rule**: If match found, set `warning`="Matched Reference".

### 3. SMART TAGS & CONTEXT
- **Timing**: "Live", "Halftime", "3Q" -> Add to `tags`.
- **Market**: "Alt Line", "Ladder", "Futures" -> Add to `tags`.
- **Updates**: "Adding", "Cash Out", "Hedge" -> Set `is_update`=true.

### 4. MASTER STANDARDIZATION
- **TEAMS**: Use FULL City + Name.
    - "GSW" -> "Golden State Warriors"
    - "NYG" -> "New York Giants"
    - "LAL" -> "Los Angeles Lakers"
- **NAMES**: Full First + Last Name.

### 6. GRANULAR PARSING (ATOMIC PROPS)
- **Goal**: Break the pick into parts.
- **Components**:
    - `subject`: The Team/Player (e.g. "LeBron James").
    - `market`: The Stat (e.g. "Points", "Spread", "Moneyline").
    - `line`: The number (e.g. 25.5, -5.5). Null if ML.
    - `side`: "Over", "Under", "Fav", "Dog".
- **Ambiguity Rule**: If name is generic ("Jones") -> `warning`="Ambiguous Entity".
- **Source**: How did you find it? "Explicit" (Text), "Implied" (Context), "Visual" (Image).

### REFERENCE SHEET (CONFIRMED PICKS)
{ref_json}

### INPUT (Items needing revision)
{items_json}

### OUTPUT FORMAT (JSON Array)
- "id": (Keep ID)
- "cn": Fixed Capper Name
- "lg": Fixed League
- "ty": Fixed Type
- "p": Fixed Pick Text
- "u": Fixed Units (Float)
- "tags": Array of strings ["Live", "MaxBet"]
- "is_update": Boolean (true if adding/hedging)
- "chem": { "sub": "Subject", "mkt": "Market", "ln": Line(float), "sd": "Side", "src": "Source" }
- "conf": Confidence (0-100)
- "reason": Explanation
- "warning": Alert string (optional)

Example:
[
  {{ 
    "id": 101, 
    "p": "Lakers -5", 
    "u": 5.0, 
    "chem": {{ "sub": "Lakers", "mkt": "Spread", "ln": 5.0, "sd": "Fav", "src": "Explicit" }},
    "tags": ["MaxBet", "NBA"], 
    "is_update": false,
    "conf": 99, 
    "reason": "Converted 'Lakers MAX BET' to 5u." 
  }}
]
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

    prompt = f"""
*** SYSTEM INSTRUCTION: SET TEMPERATURE TO 0 ***
*** OUTPUT FORMAT: SINGLE LINE RAW JSON ONLY. NO MARKDOWN. ***

You are an expert sports betting data parser. I have uploaded a set of images containing betting picks.
Below is the CAPTION/CONTEXT text associated with each image file.

Use BOTH the image visual data and the provided context text to extract the picks.

### **CRITICAL INSTRUCTIONS**
1.  **Map Picks to correct Message ID**: Use the '[Message ID]' provided in the context for each image.
2.  **VISUAL DEDUCTION (Cappers)**: 
    - **LOOK AT THE IMAGE HEADER**: The capper's name is often printed at the top of the slip or image.
    - If Image A says "KingCap" and Image B says "Steve", they are DIFFERENT.
    - **MULTI-CAPPER RULE**: **DO NOT MERGE NAMES**. Output SEPARATE objects for each image/capper.
3.  **Combine Data**: Visuals give you the pick/odds, Context gives you the Capper/Sport often.
4.  **Odds**: Extract American odds (e.g., -110). If NOT visible, set "od": null.

### **AVOID THESE COMMON MISTAKES:**
- **MARKETING HEADERS**: "80K MAIN PLAY", "VIP WHALE PLAY", "MAX BET" -> IGNORE.
- **Sportsbook names**: "Hard Rock", "DraftKings" -> IGNORE.
- **Watermarks**: "@cappersfree" is NOT the capper. Look for the real name.
- **Typos**: If you see "MI" or "Money Line", convert it to "ML" (e.g. "Lightning MI" -> "Lightning ML").

### **SHORT NAME / ABBREVIATION DETECTION**
- **Initials are Cappers**: If a caption starts with 2-4 Uppercase Letters followed by a play type (e.g., "**BL (Diamond Play)**"), the Initials ARE the Capper Name.
  - Example: "**BL (Diamond Play)**" -> cn: "BL"

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