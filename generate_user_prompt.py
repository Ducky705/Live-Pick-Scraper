import json
import os
from datetime import datetime

# Import the prompt builder directly from source to ensure we use the "Top of the Line" version
# We will copy the function here to avoid import path issues if running standalone,
# but ideally we'd import. For robustness in this script, I'll reproduce the prompt schema 
# I read from src/prompts/core.py to ensure it's exact.

PICK_FORMAT_RULES = """
RULES FOR PICK EXTRACTION:
1.  **Format**: Return strict JSON.
2.  **Entity Resolution**: "Lakers" -> Team: "Lakers", Sport: "NBA". Use the schedule if available.
3.  **Bet Type**:
    -   "Team -7" -> Spread
    -   "Team ML" or "Team Moneyline" -> Moneyline
    -   "Over 220" or "Team/Team Over 220" -> Total
    -   "Player Over 20.5 Pts" -> Player Prop
    -   "Team TT o83.5" -> Team Total (Total bet type, selection = team name)
    -   "Team/Team O 6.5 Goals" -> Game Total (Total, not a Player Prop)
4.  **Odds**: American format (-110, +200). If decimal (1.90), convert or leave as is.
5.  **Units**: "5u", "5%", "3*" (star is units), "Max Bet" (5u), "(4-UNITS)" -> 4. Default to 1.0 if missing.
6.  **Capper Name**: Identify who is making the pick.
    -   If the message says "**Dave's Picks**", capper is "Dave".
    -   If multiple cappers in one message, attribute each pick to the correct capper.
    -   CRITICAL: The first line of many messages is JUST the capper name (e.g. "Marco D'Angelo"). This is NOT a pick — it is the name of the person making the picks that follow.
    -   Common pattern: "CapperName\\n\\nLeague\\nTeam -5 (2u)" -> capper is CapperName, pick is "Team -5".
    -   Separator patterns: "➖➖➖➖➖" or "---" or "➖" between cappers.
    -   Emoji patterns: 🔮, #, @, ✅ before capper names are labels, not picks.
7.  **NOISE FILTER (CRITICAL)**:
    -   Do NOT extract capper names ("Marco D'Angelo", "Tokyo Brandon", "King Of The Court") as picks.
    -   Do NOT extract book names ("Hard Rock", "FanDuel", "Caesars", "DraftKings", "BetRivers", "MGM") as picks.
    -   Do NOT extract timestamps ("08:50 am", "2:00pm PST", "16:19") as parts of picks.
    -   Do NOT extract reaction/view counts ("7 👁️", "🔥 24", "172 @") as parts of picks.
    -   Do NOT extract section headers ("NCAAB PLAYS", "CBB ADD", "FULL CARD", "Saturday Card") as picks.
    -   Do NOT extract ticket/bet slip metadata ("Ticket#", "Status Pending", "Risk/Win", "Selection NCAA") as picks.
    -   Do NOT extract commentary ("Crazy choke from Florida", "Let's get it") as picks.
    -   Do NOT extract "Straight Bets Only", "Recap", or "Results" as picks.
    -   IGNORE: "Dm for vip", "Link in bio", "Promo", "Sign up", URLs.
8.  **MULTI-CAPPER MESSAGES**: Many messages contain picks from MULTIPLE cappers. Extract ALL of them.
    -   Pattern A: "🔮Capper1\\nLeague1\\nPick1\\n🔮Capper2\\nLeague2\\nPick2"
    -   Pattern B: "Capper1\\n➖➖➖➖➖\\nPick1\\nCapper2\\n➖➖➖➖➖\\nPick2"
    -   Pattern C: "#Capper1\\nPick1\\n#Capper2\\nPick2"
    -   You MUST attribute each pick to the correct capper.
    -   Do NOT stop after the first capper — scan the ENTIRE message.
"""

def generate_prompt(raw_data_lines):
    current_date = "2026-02-14"
    
    return f"""You are an expert Sports Betting Analyst. Your goal is to extract valid betting picks from raw text with 100% accuracy.

DATA INPUT FORMAT:
### [MessageID]
[Text content...]

{PICK_FORMAT_RULES}

CRITICAL INSTRUCTION:
1.  Perform a "Mental Verification" step for every potential pick.
2.  **EXTRACT ALL VALID PICKS**. Do not stop after the first one. Scan the entire text.
3.  Verify: "Is 'BetSharper' a team?" -> No. -> Skip.
4.  Verify: "Is 'Lakers -5' a bet?" -> Yes. -> Extract.

OUTPUT FORMAT (JSON):
{{
  "picks": [
    {{
      "message_id": "12345",
      "capper_name": "Name",
      "sport": "NBA/NFL/NCAAB/etc",
      "bet_type": "Spread/Moneyline/Total/Player Prop",
      "selection": "Lakers -5",
      "line": -5.0,
      "odds": -110,
      "units": 1.0,
      "confidence": 9,
      "reasoning": "Explicit mention of Lakers spread"
    }}
  ]
}}

If no valid picks are found, return {{ "picks": [] }}.

DATA TO PROCESS:
{raw_data_lines}
"""

def main():
    input_file = r"src\data\output\picks_2026-02-14_raw.json"
    output_file = r"golden_set_prompt.txt"

    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Dedup logic: use _source_text as unique identifier
    seen_texts = set()
    unique_items = []
    
    # We'll take the first 30 UNIQUE items to make a solid prompt
    # Limits file size for copy-pasting
    LIMIT = 30
    
    for item in data:
        text = item.get("_source_text", "").strip()
        msg_id = item.get("message_id", "0")
        
        if not text:
            continue
            
        if text not in seen_texts:
            seen_texts.add(text)
            unique_items.append({
                "id": msg_id,
                "text": text
            })
            
        if len(unique_items) >= LIMIT:
            break

    # Format the data block
    data_block_lines = []
    for item in unique_items:
        data_block_lines.append(f"### [{item['id']}]")
        data_block_lines.append(item['text'])
        data_block_lines.append("") # Blank line separator

    raw_data_str = "\n".join(data_block_lines)

    # Generate full prompt
    full_prompt = generate_prompt(raw_data_str)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_prompt)

    print(f"Successfully generated {output_file} with {len(unique_items)} unique items.")

if __name__ == "__main__":
    main()
