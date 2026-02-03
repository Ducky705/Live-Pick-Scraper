from datetime import datetime
from typing import Any

# =============================================================================
# COMPACT SCHEMA DEFINITIONS
# =============================================================================

# Key mapping: compact -> full (for documentation, actual expansion in decoder.py)
COMPACT_SCHEMA = {
    "i": "message_id",
    "c": "capper_name",
    "l": "league",
    "t": "type",
    "p": "pick",
    "o": "odds",
    "u": "units",
    "d": "date",
}

# Type abbreviations (2 chars max for output efficiency)
TYPE_ABBREV = {
    "ML": "Moneyline",
    "SP": "Spread",
    "TL": "Total",
    "PP": "Player Prop",
    "TP": "Team Prop",
    "GP": "Game Prop",
    "PD": "Period",
    "PL": "Parlay",
    "TS": "Teaser",
    "FT": "Future",
    "UK": "Unknown",
}

# Reverse mapping for prompt instructions
TYPE_FULL_TO_ABBREV = {v: k for k, v in TYPE_ABBREV.items()}

# Valid leagues (already compact)
LEAGUES = [
    "NFL",
    "NCAAF",
    "NBA",
    "NCAAB",
    "WNBA",
    "MLB",
    "NHL",
    "EPL",
    "MLS",
    "UCL",
    "UFC",
    "PFL",
    "TENNIS",
    "SOCCER",
    "EUROLEAGUE",
    "PGA",
    "F1",
    "Other",
]

# Stat abbreviations for props
STAT_ABBREVS = {
    # Basketball
    "Pts": "Points",
    "Reb": "Rebounds",
    "Ast": "Assists",
    "Blk": "Blocks",
    "Stl": "Steals",
    "3PM": "3-Pointers Made",
    "PRA": "Pts+Reb+Ast",
    # Football
    "PassYds": "Passing Yards",
    "RushYds": "Rushing Yards",
    "RecYds": "Receiving Yards",
    "PassTD": "Passing TDs",
    "Rec": "Receptions",
    "Comp": "Completions",
    # Baseball
    "K": "Strikeouts",
    "H": "Hits",
    "HR": "Home Runs",
    "RBI": "RBIs",
    "TotalBases": "Total Bases",
    # Hockey
    "SOG": "Shots on Goal",
    "G": "Goals",
    "A": "Assists",
    "P": "Points",
}

# Noise keywords to skip (marketing, watermarks, etc.)
NOISE_KEYWORDS = [
    "VIP",
    "WHALE",
    "MAX BET",
    "LOCK",
    "80K",
    "GUARANTEED",
    "@cappersfree",
    "@freepicks",
    "@vippicks",
    "POTD",
    "Join",
    "DM for",
    "FREE PLAY",
]

# Ultra-compact schema doc for prompts (~150 chars vs ~800 original)
SCHEMA_DOC = """KEYS:i=id,c=capper(ANCHOR:Look at FIRST LINE of text. REQUIRED),l=league(ANCHOR:Infer from teams. REQUIRED),t=type,p=pick,o=odds(int),u=units(float),q=confidence(1-10)
TYPES:ML,SP,TL,PP,TP,GP,PD,PL,TS,FT,UK
LEAGUES:NFL,NCAAF,NBA,NCAAB,WNBA,MLB,NHL,EPL,MLS,UCL,UFC,PFL,TENNIS,SOCCER,PGA,F1,ESPORTS,Other"""

# Pick format rules (compressed from 100+ line formatting guide)
PICK_FORMAT_RULES = """FORMATS:
ML=Team ML|SP=Team -7.5|TL=Team A vs B O/U X
PP=Name: Stat O/U X|TP=Team: Stat O/U X|GP=Team/Event: Prop
PD=1H Team -5|PL=(LG) Leg1 / (LG) Leg2
RULES:
1.Type: "Team -7"=SP. "Team ML"=ML. "Team (+105)"=ML(Odds). "Over X"=TL/TP.
2.Totals: "Lakers/Clippers Under 222.5"=TL (Matchup Separator /).
3.Names: "William & Mary","Texas A&M" are SINGLE TEAMS (NCAAB).
4.Parlays: "Team A / Team B" or "Team A + Team B"=PL. "2-Team Parlay:"=Combine lines below.
5.Split: "Parlay 1, Parlay 2" or "1., 2." are SEPARATE picks. Output ALL 1-N.
6.Polarity: NEVER FLIP OVER/UNDER. Source "Under" -> Output "Under".
7.Odds: >100 or <-100 are ODDS (o field). <20 are SPREADS (p string).
8.Period: Must start with 1H/1Q. "1H Team -5".
9.Tennis: "Name -1.5 sets" (No ML). "Name ML".
10.Multi-Sport: l=Other. Legs get (LEAGUE) prefix. "De Minaur/Warriors"=(TENNIS)/(NBA)."""

# Noise filter instruction
NOISE_FILTER = """MARKETING: Ignore headers/words like 'VIP','WHALE','MAX BET','LOCK','80K','GUARANTEED'. Do NOT use them as Capper Name. EXTRACT picks underneath."""

# Negative constraints (new)
NEGATIVE_CONSTRAINTS = """CONSTRAINTS:
1.NOISE: Ignore "VIP", "80K", "MAX", "@cappersfree", "Promo".
2.ISOLATION: Picks MUST match their source "i". RESET context per message. NEVER cross-contaminate teams/odds between messages.
3.ALL PICKS: If message lists 10 picks, output 10 objects. SCAN ENTIRE TEXT.
4.POLARITY: "Under" -> "Under". NEVER flip.
5.ODDS: +/-100+ goes in "o". <20 goes in "p".
6.PROPS: "Team 60-Min" -> Include Team Name.
7.FUTURES: "Event: Selection". t=FT.
8.PERIOD: Start pick with "1H"/"1Q".
9.CAPPER: Use FIRST LINE. Ignore 'Text'/'Caption'."""


# =============================================================================
# PROMPT BUILDER FUNCTIONS
# =============================================================================


def get_compact_extraction_prompt(raw_data: str, current_date: str | None = None) -> str:
    """
    Generate ultra-compact extraction prompt.

    Token reduction: ~67% (from ~1200 to ~400 tokens)

    Args:
        raw_data: The formatted raw message data (### id [T] text [OCR] ocr)
        current_date: Date string (YYYY-MM-DD), defaults to today

    Returns:
        Compact prompt string
    """
    if not current_date:
        current_date = datetime.now().strftime("%Y-%m-%d")

    return f"""TEMP:0 OUTPUT:JSON(1 line,no markdown)
Extract ALL betting picks.

{SCHEMA_DOC}
{PICK_FORMAT_RULES}
{NOISE_FILTER}
{NEGATIVE_CONSTRAINTS}

RULES:
1.i=id: COPY EXACT ID from "### id".
2.c=capper: FIRST LINE (default). If headers present (e.g. 🔮), use header for section.
3.l=league: Infer (Lakers->NBA).
4.o=odds (int): -110, +150.
5.u=units: "5u"->5. "Max"->5. "Whale"->10. Default 1.
6.LISTS: EXTRACT EVERY SINGLE PICK. If 50 items, output 50 items. DO NOT SUMMARIZE.
7.PARLAYS: "Team A + Team B" = t=PL. Legs: (LG) Leg1 / (LG) Leg2.
8.SPLIT: "Team +8 & ML" = 2 picks.
9.CONFIDENCE (q): 1-10.

OUTPUT:{{"picks":[{{"i":12345,"c":"Name","l":"NBA","t":"PP","p":"LeBron: Pts O 25.5","o":-110,"u":1,"r":"Found prop"}},{{"i":12345,"c":"Name","l":"NBA","t":"ML","p":"Lakers ML","o":-150,"u":1}}]}}

DATA:
{raw_data}"""


def get_compact_revision_prompt(failed_items: list[dict[str, Any]]) -> str:
    """
    Generate compact revision/refinement prompt for failed extractions.

    Args:
        failed_items: List of items with failed fields

    Returns:
        Compact revision prompt
    """
    import json

    # Minify the input data
    minified = []
    for item in failed_items:
        entry = {
            "i": item.get("message_id") or item.get("id"),
            "fails": item.get("fails", []),
            "ctx": (item.get("original_text", "") or item.get("context", ""))[:3000],
        }
        if item.get("pick"):
            entry["p"] = item.get("pick")
        minified.append(entry)

    items_json = json.dumps(minified, separators=(",", ":"))

    return f"""TEMP:0.1 OUTPUT:JSON(1 line)
Re-analyze failed fields using context.

TIPS:
1.i=id: COPY FROM INPUT.
2.c=capper at top of image/text
3.l=league from team names
4.p=pick "Team -7.5" or "Team ML"

NOISE:If p has "80K","VIP","MAX BET"->find real bet or p=null

INPUT:{items_json}

OUTPUT:[{{"i":12345,"c":"Name","l":"NBA","p":"Team -5"}}]"""


def get_dsl_extraction_prompt(raw_data: str, current_date: str | None = None) -> str:
    """
    Generate DSL extraction prompt (Pipe-Delimited) with Chain-of-Thought.

    Format:
    <analysis>
    ... reasoning ...
    </analysis>
    id|capper|league|type|pick|odds|units|reasoning

    Args:
        raw_data: The formatted raw message data
        current_date: Date string (YYYY-MM-DD)

    Returns:
        DSL prompt string
    """
    if not current_date:
        current_date = datetime.now().strftime("%Y-%m-%d")

    return f"""TEMP:0.1 OUTPUT:TEXT
Extract betting picks.
STEP 1: Analyze the message in an <analysis> block.
- Identify the SPORT (College vs Pro). "William & Mary" is a College Team, NOT a parlay.
- Identify the BET TYPE. "Team Total" != "Game Total". "Team -7" = Spread. "Team ML" = Moneyline.
- Check for LISTS. Extract ALL items (Parlay 1, Parlay 2...).
- Check for "Team1 + Team2" (Parlay) vs "Team1 vs Team2" (Game).

STEP 2: Output picks in strict pipe-separated format (one per line).
id|capper|league|type|pick|odds|units|reasoning

{SCHEMA_DOC}
{PICK_FORMAT_RULES}

CRITICAL RULES:
1. LEAGUE:
   - "William & Mary", "Charleston", "Hofstra" -> NCAAB (College Basketball).
   - "Lakers", "Celtics" -> NBA.
2. TYPE:
   - "Team Total Over X" -> TP (Team Prop).
   - "Team A vs Team B Over X" -> TL (Game Total).
   - "Team -7" -> SP (Spread). "Team ML" -> ML.
3. PARLAYS:
   - "Team A + Team B" -> Parlay.
   - "Team A / Team B" -> Parlay.
   - Output as: (LEAGUE) Leg 1 / (LEAGUE) Leg 2
4. FORMAT:
   - 1H/1Q bets MUST start with "1H" or "1Q".
   - Props: "Player: Stat Over/Under X".
5. ID MAPPING (CRITICAL):
   - The "id" column MUST match the `### id` from the DATA section.
   - Do NOT use sequential numbers (1, 2, 3). Use the actual Message ID (e.g. 12806).
   - If a message has multiple picks, repeat the same Message ID for each line.

EXAMPLES:
Input: "### 12345 [Dave] William & Mary +4.5 and Hofstra -3. Also Lakers Over 220."
Output:
<analysis>
1. "William & Mary" is a single college team (NCAAB). +4.5 is a spread.
2. "Hofstra" is NCAAB. -3 is a spread.
3. "Lakers Over 220" implies Lakers vs Opponent Game Total (NBA).
</analysis>
12345|Dave|NCAAB|SP|William & Mary +4.5|-110|1.0|Spread bet
12345|Dave|NCAAB|SP|Hofstra -3|-110|1.0|Spread bet
12345|Dave|NBA|TL|Lakers vs Opponent Over 220|-110|1.0|Game Total

DATA:
{raw_data}"""


def get_compact_ocr_batch_prompt(n: int) -> str:
    """
    Generate ultra-compact OCR batch prompt.

    Token reduction: ~70% (from ~100 to ~30 tokens)

    Args:
        n: Number of images in batch

    Returns:
        Compact OCR batch prompt
    """
    return f'Extract text from {n} images. Return JSON array of {n} strings:["text1","text2"]. Combine each image\'s text into 1 string with \\n. No markdown.'


def get_compact_vision_prompt() -> str:
    """
    Generate compact one-shot vision parsing prompt.

    Returns:
        Compact vision prompt for direct image parsing
    """
    return f"""Extract betting picks from this image. Return JSON only.

{SCHEMA_DOC}
{PICK_FORMAT_RULES}

RULES:
1.Infer league from team/player names
2.Ignore watermarks(@cappersfree),ads
3.c=capper name if visible,else "Unknown"
4.Parlay:list each leg with (LEAGUE) prefix

OUTPUT:{{"picks":[{{"i":0,"c":"Name","l":"NBA","t":"SP","p":"Lakers -5","o":-110,"u":1}}]}}"""


def get_compact_judge_prompt() -> str:
    """
    Generate compact judge/oracle prompt for ground truth detection.

    Returns:
        Compact judge system prompt
    """
    return """Sports betting pick detector. Find picks in messages.

VALID PICK=team/player name + bet indicator(-5,ML,Over 220,+3.5)
IGNORE:VIP promos,recaps with checkmarks,bankroll advice,sportsbook names alone

Extract:capper,picks array,confidence(1-10)
Output JSON only."""


def get_compact_auditor_prompt(context_text: str, current_picks_json: str) -> str:
    """
    Generate compact auditor/refiner prompt.

    Args:
        context_text: Original text and OCR content
        current_picks_json: Current extracted picks as JSON string

    Returns:
        Compact auditor prompt
    """
    return f"""TEMP:0.1 Sports Betting Auditor. Verify and fix picks.

CONTEXT:
{context_text[:1500]}

CURRENT PICKS:
{current_picks_json}

TASKS:
1.Compare picks to context
2.Fix errors(wrong odds,teams,Unknown fields)
3.Remove duplicates
4.c=capper from @handle or name
5.l=league from team names
6.t=ML,SP,TL,PP,TP,GP,PD,PL,TS,FT,UK
7.Skip noise(Whale,Max Bet,Guaranteed)
8.If no picks,return empty []

OUTPUT:{{"picks":[{{"i":123,"c":"Dave","l":"NBA","p":"Lakers -5","u":1}}]}}"""


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def compress_raw_data(selected_data: list[dict[str, Any]]) -> str:
    """
    Compress raw message data for prompt input.

    Matches the format expected by extraction prompts:
    ### id [T] text [OCR 1] ocr_text

    Args:
        selected_data: List of message dicts with id, text, ocr_texts

    Returns:
        Compressed data string
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
                entry += f" [OCR {i + 1}] {cleaned}"

        lines.append(entry)

    return "\n".join(lines)
