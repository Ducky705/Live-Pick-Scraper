from datetime import datetime
from typing import Any
import json

# =============================================================================
# ACCURACY-FIRST SCHEMA DEFINITIONS
# =============================================================================

PICK_FORMAT_RULES = """
RULES FOR PICK EXTRACTION:
1.  **Format**: Return strict JSON.
2.  **Goal**: EXTRACT EVERY SINGLE BETTING LINE. Do not aim for perfection, aim for COMPLETENESS.
3.  **Bet Verification**:
    -   If it has a Team Name + Number (e.g. "Lakers -5", "Bulls +110"), IT IS A BET.
    -   If it has "Over" or "Under" + Number (e.g. "Over 220.5"), IT IS A BET.
    -   If it says "ML" or "Moneyline", IT IS A BET.
    -   If it says "units" or "u" (e.g. "3u", "Max Play"), IT IS A BET.
4.  **Handling Headers**:
    -   Lines like "HammeringHank" or "5 Unit Play" are Context/Headers. Use them to fill `capper_name` and `units` fields for the picks below them.
    -   If you see a new name, switch `capper_name` for subsequent picks.
5.  **Noise Handling**:
    -   Ignore: "DM for VIP", urls, "Link in bio", "Promo".
    -   Capture: "Analysis", "Writeup" -> put in `reasoning` field if short, otherwise ignore.
6.  **MULTI-PICK & PARLAY HANDLING**:
    -   Extract each leg of a parlay as a separate pick if listed separately.
    -   If listed as "Team A / Team B / Team C", extract as one pick with type "Parlay".
"""

# =============================================================================
# PROMPT BUILDER FUNCTIONS
# =============================================================================


BATCH_EXAMPLE = """
EXAMPLE INPUT 1 (Dense Multi-Capper Message):
### [9001]
SmartMoney Vanderbilt -6.5 NC State -5.5 Arizona -9.5
CashC Iowa State -6 Clemson +13.5

EXAMPLE OUTPUT 1:
{
  "picks": [
    { "message_id": "9001", "capper_name": "SmartMoney", "sport": "NCAAB", "bet_type": "Spread", "selection": "Vanderbilt -6.5", "line": -6.5, "odds": null, "units": 1.0, "confidence": 9, "reasoning": "Explicit spread" },
    { "message_id": "9001", "capper_name": "SmartMoney", "sport": "NCAAB", "bet_type": "Spread", "selection": "NC State -5.5", "line": -5.5, "odds": null, "units": 1.0, "confidence": 9, "reasoning": "Explicit spread" },
    { "message_id": "9001", "capper_name": "SmartMoney", "sport": "NCAAB", "bet_type": "Spread", "selection": "Arizona -9.5", "line": -9.5, "odds": null, "units": 1.0, "confidence": 9, "reasoning": "Explicit spread" },
    { "message_id": "9001", "capper_name": "CashC", "sport": "NCAAB", "bet_type": "Spread", "selection": "Iowa State -6", "line": -6.0, "odds": null, "units": 1.0, "confidence": 9, "reasoning": "Explicit spread" },
    { "message_id": "9001", "capper_name": "CashC", "sport": "NCAAB", "bet_type": "Spread", "selection": "Clemson +13.5", "line": 13.5, "odds": null, "units": 1.0, "confidence": 9, "reasoning": "Explicit spread" }
  ]
}
NOTE: ALL 5 picks extracted. Each capper's picks are separate entries.

EXAMPLE INPUT 2 (Mixed Sports):
### [9002]
LearLocks Olympics hockey Czechia ML 1.5u -135
Tennis Yastremska ML 1.5u -115

EXAMPLE OUTPUT 2:
{
  "picks": [
    { "message_id": "9002", "capper_name": "LearLocks", "sport": "Hockey", "bet_type": "Moneyline", "selection": "Czechia", "line": null, "odds": -135, "units": 1.5, "confidence": 9, "reasoning": "Explicit ML" },
    { "message_id": "9002", "capper_name": "LearLocks", "sport": "Tennis", "bet_type": "Moneyline", "selection": "Yastremska", "line": null, "odds": -115, "units": 1.5, "confidence": 9, "reasoning": "Explicit ML" }
  ]
}
NOTE: Sport changes mid-message. Each pick gets its correct sport.
"""

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

    return f"""You are an expert Sports Betting Analyst. Your goal is to extract valid betting picks from a BATCH of raw text messages with 100% accuracy.

DATA INPUT FORMAT:
The input contains multiple messages separated by headers:
### [MessageID]
[Text content...]

{schedule_section}{style_section}
{PICK_FORMAT_RULES}
{BATCH_EXAMPLE}

CRITICAL INSTRUCTION:
1.  **BATCH PROCESSING**: The input contains MULTIPLE messages (e.g. ### [ID1], ### [ID2]). You must process EVERY SINGLE message.
2.  **ITERATION**: Read ### [ID1], extract picks. Then read ### [ID2], extract picks. Repeat until the end.
3.  **DO NOT STOP** after the first message.
4.  Perform a "Mental Verification" step for every potential pick.
5.  Verify: "Is 'Lakers -5' a bet?" -> Yes. -> Extract.

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
      "confidence": 9.5,
      "reasoning": "Found valid spread pattern 'Lakers -5'",
      "_source_text": "Lakers -5 (2u)"
    }}
  ]
}}

RAW DATA TO PROCESS:
{raw_data}
"""

def normalize_response(
    raw_response: str,
    expand: bool = False,
    valid_message_ids: list[str] | None = None,
    message_context: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """
    Parses the JSON response from the LLM.
    Handles markdown blocks, partial JSON, and simple syntax errors.
    """
    cleaned_json = raw_response.strip()
    
    # Remove markdown code blocks
    if cleaned_json.startswith("```json"):
        cleaned_json = cleaned_json.replace("```json", "").replace("```", "").strip()
    elif cleaned_json.startswith("```"):
        cleaned_json = cleaned_json.replace("```", "").strip()

    try:
        data = json.loads(cleaned_json)
        
        # Determine format
        if isinstance(data, list):
            picks = data
        elif isinstance(data, dict):
            if "picks" in data:
                picks = data["picks"]
            elif "bets" in data:
                picks = data["bets"]
            elif "data" in data and isinstance(data["data"], list):
                picks = data["data"]
            else:
                # Last resort: if the dict itself looks like a pick, wrap it
                if "selection" in data or "pick" in data:
                    picks = [data]
                else:
                    return []
        else:
            return []

        # Basic cleanup
        normalized_picks = []
        for p in picks:
            # Flatten compressed keys if present (from older prompts)
            # "p" -> "pick", "o" -> "odds", etc.
            if "p" in p and "pick" not in p: p["pick"] = p["p"]
            if "o" in p and "odds" not in p: p["odds"] = p["o"]
            if "u" in p and "units" not in p: p["units"] = p["u"]
            if "t" in p and "type" not in p: p["type"] = p["t"]
            if "l" in p and "league" not in p: p["league"] = p["l"]
            if "c" in p and "capper_name" not in p: p["capper_name"] = p["c"]
            if "r" in p and "reasoning" not in p: p["reasoning"] = p["r"]
            if "i" in p and "message_id" not in p: p["message_id"] = p["i"]

            # Cap confidence
            if "confidence" in p:
                try:
                    conf = float(p["confidence"])
                    if conf > 10: p["confidence"] = 10
                except:
                    p["confidence"] = 5.0

            normalized_picks.append(p)

        return normalized_picks

    except json.JSONDecodeError:
        return []

# Alias for compatibility
get_compact_extraction_prompt = get_reasoning_extraction_prompt
get_compact_revision_prompt = get_reasoning_extraction_prompt
get_dsl_extraction_prompt = get_reasoning_extraction_prompt
get_cot_extraction_prompt = get_reasoning_extraction_prompt

def compress_raw_data(data: list[dict[str, Any]] | str) -> str:
    """
    Compresses input data into a dense text format for the AI prompt.
    Handles both raw lists of messages and pre-formatted strings.
    """
    import re

    if isinstance(data, list):
        # Convert list of messages to the standard text format
        # Format:
        # ### [MessageID]
        # [Text]
        # [OCR - optional]
        buffer = []
        for msg in data:
            m_id = msg.get("id", "Unknown")
            text = msg.get("text", "")
            ocr = msg.get("ocr_text", "")
            
            buffer.append(f"### [{m_id}]")
            if text:
                buffer.append(text.strip())
            if ocr:
                buffer.append(f"[OCR]: {ocr.strip()}")
            buffer.append("") # Separator
        
        text = "\n".join(buffer)
    else:
        text = str(data)

    # Standard cleanup
    return re.sub(r'\n{3,}', '\n\n', text).strip()
