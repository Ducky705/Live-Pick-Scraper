from datetime import datetime
from typing import Any
import json

# =============================================================================
# ACCURACY-FIRST SCHEMA DEFINITIONS
# =============================================================================

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

# =============================================================================
# PROMPT BUILDER FUNCTIONS
# =============================================================================


def get_reasoning_extraction_prompt(
    raw_data: str,
    current_date: str | None = None,
    schedule_context: str | None = None,
    style_context: str | None = None,
) -> str:
    """
    Generate a verbose, Chain-of-Thought extraction prompt.
    Prioritizes ACCURACY over token usage.
    """
    if not current_date:
        current_date = datetime.now().strftime("%Y-%m-%d")

    schedule_section = ""
    if schedule_context:
        schedule_section = f"SCHEDULE CONTEXT ({current_date}):\n{schedule_context}\n\n"

    style_section = ""
    if style_context:
        style_section = f"CAPPER STYLE GUIDE:\n{style_context}\n\n"

    return f"""You are an expert Sports Betting Analyst. Your goal is to extract valid betting picks from raw text with 100% accuracy.

DATA INPUT FORMAT:
### [MessageID]
[Text content...]
[OCR content...]

{schedule_section}{style_section}
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
{raw_data}"""


def get_compact_extraction_prompt(
    raw_data: str,
    current_date: str | None = None,
    schedule_context: str | None = None,
    style_context: str | None = None,
) -> str:
    """
    Backward compatibility alias. Redirects to reasoning prompt.
    """
    return get_reasoning_extraction_prompt(
        raw_data, current_date, schedule_context, style_context
    )


def get_compact_revision_prompt(failed_items: list[dict[str, Any]]) -> str:
    """
    Generate a reasoning-based revision prompt.
    """
    # Simply json dump the failed items for clarity
    items_str = json.dumps(failed_items, indent=2)

    return f"""You are fixing failed extractions.
The following picks were flagged as invalid or incomplete.
Please re-analyze the context and correct them.

FAILED ITEMS:
{items_str}

INSTRUCTIONS:
1. Check the 'original_text' or 'context'.
2. If the pick is valid but malformed, fix it.
3. If it was NOT a pick (e.g. a header, garbage), return "action": "delete".
4. If it was a duplicate, return "action": "delete".

OUTPUT JSON:
{{
  "corrections": [
    {{
      "message_id": "...",
      "selection": "Corrected Selection",
      "action": "fix" 
    }}
  ]
}}
"""


def get_dsl_extraction_prompt(raw_data: str, current_date: str | None = None) -> str:
    """
    Legacy DSL prompt. Kept if needed, but we prefer JSON.
    """
    return get_reasoning_extraction_prompt(raw_data, current_date)


def compress_raw_data(selected_data: list[dict[str, Any]]) -> str:
    """
    Prepare raw data for the prompt.
    Keeps the ### ID format as it is clean and robust.
    """
    from src.utils import clean_text_for_ai

    lines = []
    for item in selected_data:
        entry = f"### {item['id']}"

        text = clean_text_for_ai(item.get("text", ""))
        ocr_texts = item.get("ocr_texts", [])

        # Fallback to legacy field
        if not ocr_texts and item.get("ocr_text"):
            ocr_texts = [item.get("ocr_text")]

        if text:
            entry += f"\n{text}"

        for i, ocr in enumerate(ocr_texts):
            cleaned = clean_text_for_ai(ocr)
            if cleaned:
                entry += f"\n[OCR] {cleaned}"

        lines.append(entry)

    return "\n".join(lines)
