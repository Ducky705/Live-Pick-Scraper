from datetime import datetime
from typing import List, Dict, Any, Optional

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
SCHEMA_DOC = """KEYS:i=id,c=capper(First line of text/header. If unknown use 'Unknown'),l=league,t=type,p=pick,o=odds(int,e.g.-110),u=units(float),q=confidence(1-10)
TYPES:ML,SP,TL,PP,TP,GP,PD,PL,TS,FT,UK
LEAGUES:NFL,NCAAF,NBA,NCAAB,WNBA,MLB,NHL,EPL,MLS,UCL,UFC,PFL,TENNIS,SOCCER,PGA,F1,Other"""

# Pick format rules (compressed from 100+ line formatting guide)
PICK_FORMAT_RULES = """PICK FORMATS:
ML=Team ML|SP=Team -7.5|TL=Team A vs B O/U X
PP=Name: Stat O/U X|TP=Team: Stat O/U X|GP=Team/Event: Period/Prop Type
PD=1H Team -5 OR 1H Team vs Team O/U X (MUST start with 1H/1Q)|PL=(LG) Leg1 / (LG) Leg2|FT=Event: Selection
TENNIS:Name ML|Name +/-X sets|Name +/-X games|A vs B O/U X games
PERIOD TRIGGERS:1H,2H,1Q,2Q,3Q,4Q,F5,F3,P1,P2,P3,"First Half","First 5"
STATS:Pts,Reb,Ast,PRA,PassYds,RushYds,RecYds,PassTD,Rec,K,H,HR,RBI,SOG,G,A

CRITICAL TYPE RULES:
-If pick has "Team -7" or "Team +3.5" (number after team): t=SP (Spread), NOT ML
-If pick has "ML" explicitly: t=ML
-If pick has "Over X" or "Under X" with two teams: t=TL (Total)
-CRITICAL: "Lakers/Clippers Under 222.5" is t=TL (Total), NOT Parlay! The "/" is a matchup separator
-CRITICAL: "William & Mary ML" is ONE team (college), NOT a parlay! "&" is part of the name
-COMPOUND TEAM NAMES (NOT parlays): William & Mary, Texas A&M, Simon Fraser
-If pick has "Team A / Team B" with ML/Spread for EACH: t=PL (Parlay)
-If pick has single team Over/Under (no opponent): t=TP (Team Prop), e.g., "Magic Over 114.5"
-Parlay 1, Parlay 2, etc. are SEPARATE picks with t=PL
-CRITICAL: "Team1 + Team2 (-140)" = Parlay with 2 legs, not single ML

PARLAY LEAGUE RULES:
-If ALL legs are same league (e.g., all NBA), set l=NBA (NOT Other).
-If legs are mixed (NBA + NFL), set l=Other.
-ALWAYS use (LEAGUE) prefix for EVERY leg in p field, even if same league.

TENNIS FORMATTING:
-Sets/Games spreads: "Name -1.5 sets" or "Name -4.5 games".
-NEVER append "ML" to set/game spreads (Invalid: "Name -1.5 sets ML").
-NEVER use "/" inside a leg description. It breaks parlay splitting.

OVER/UNDER POLARITY (CRITICAL - NEVER FLIP):
-If source says "UNDER 222.5", output MUST be "Under 222.5" - NEVER change to "Over"
-If source says "OVER 150.5", output MUST be "Over 150.5" - NEVER change to "Under"
-ALWAYS preserve the EXACT polarity (Over/Under) from the source text
-This is a FATAL ERROR if flipped - bets are opposite outcomes

ODDS VS SPREAD DISTINCTION:
-Numbers 100+ are American ODDS (e.g., +105, -110), NOT spreads
-"Team (+105)" means Moneyline at +105 odds, NOT spread of +105 points
-"Team +3.5" is a Spread (small number with decimal)
-"Team -7" is a Spread (single digit number)
-Put odds in "o" field, NOT in pick string

GAME PROPS / PERIOD PROPS:
-"Team 60-Min ML" = Game Prop for 60-minute regulation result
-"Vegas Golden Knights 60-MIN REGULATION" = pick should be "Vegas Golden Knights 60-Min ML"
-ALWAYS include team name with period/regulation props
-Format: "Team Name: Period/Prop Type" or "Team Name Period ML"
-PERIOD BETS: MUST START WITH PERIOD (e.g. "1H George Mason -6")

LIST/ENUMERATED PARSING (CRITICAL):
-ALWAYS extract ALL items from numbered/labeled lists (Parlay 1, Parlay 2, Parlay 3... Parlay 7)
-Each "Parlay N:" or numbered item (1., 2., 3.) is a SEPARATE pick row
-"Duck Parlay:" or similar labels = one parlay pick per label
-NEVER skip items in a list. If message has "Parlay 1" through "Parlay 7", output 7 picks
-SCAN ENTIRE MESSAGE - first and last items in lists are commonly missed

CROSS-SPORT PARLAY RULES:
-"De Minaur/Warriors MLP" = cross-sport parlay: t=PL, l=Other, p="(TENNIS) De Minaur ML / (NBA) Warriors ML"
-MLP = Moneyline Parlay. Always t=PL
-When parlay has legs from different sports, l=Other and EACH leg gets (LEAGUE) prefix
-Tennis players: De Minaur, Alcaraz, Sinner, Djokovic, Swiatek, Gauff, etc. -> l=TENNIS

MULTI-PICK STRING RULE:
-If a string contains multiple distinct picks (e.g., "Bublik ML De Minaur ML Alcaraz 3:0 Paul +1.5 sets"):
-Split into SEPARATE pick rows, one per bet. DO NOT output as single mashup string."""

# Noise filter instruction
NOISE_FILTER = """SKIP:VIP,WHALE,MAX BET,LOCK,80K,GUARANTEED,@watermarks,records,sportsbook names,recaps with checkmarks"""

# Negative constraints (new)
NEGATIVE_CONSTRAINTS = """CONSTRAINTS:
1.DO NOT use "80K", "VIP", "MAX" as picks. These are noise.
2.DO NOT use "@cappersfree" or watermarks as capper name.
3.If "80K" is present, u=80000.
4.If no clear bet, p=null.
5.CRITICAL MESSAGE ISOLATION: Each pick MUST use the exact "i" (message_id) from its source message.
  -NEVER mix teams/entities from one message into another message's picks
  -NEVER carry over context (team names, player names) between ### message blocks
  -If Message A mentions "Oilers" and Message B mentions "60-MIN", do NOT output Oilers for Message B
  -Treat each ### block as completely independent. Reset your context after each message.
6.OUTPUT EVERY PICK: If message has Parlay 1-7, output 7 separate rows. Never skip items in lists.
7.POLARITY LOCK: If source says "UNDER", output must contain "Under". NEVER flip to "Over".
8.ODDS IN FIELD: +/-100+ numbers are odds, put in "o" field. Do NOT put in pick string.
9.GAME PROPS: "Team 60-Min ML" or "Team Regulation" must include team name in pick.
10.FUTURE BETS: Use "Event: Selection" format. (e.g. "Super Bowl: Rams").
  -Do NOT treat futures as Moneyline. t=FT.
  -Extract odds (e.g. +225) into "o" field.
11.PERIOD FORMAT: "1H Team -X". Prefix 1H/1Q is MANDATORY in pick string.
12.CAPPER NAME: DO NOT use 'Text', 'Caption', 'OCR', 'Content', 'T' as capper name. Look at the FIRST LINE of [CONTENT]."""


# =============================================================================
# PROMPT BUILDER FUNCTIONS
# =============================================================================


def get_compact_extraction_prompt(
    raw_data: str, current_date: Optional[str] = None
) -> str:
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
Extract betting picks from data below.

{SCHEMA_DOC}
{PICK_FORMAT_RULES}
{NOISE_FILTER}
{NEGATIVE_CONSTRAINTS}

RULES:
1.c=capper from header/username/CAPPER: tag. Check FIRST LINE of [CONTENT] for name. Ignore "Content"/"Caption".
2.o=American odds int(-110,+150) or null if not visible. DO NOT GUESS -110.

3.u=units float. CHECK HEADERS (e.g."10U MAX"). Default 1.
4.Separate picks per capper.
5.Period bets:if text has 1H/1Q/F5/P1, t=PD.
6.Parlay:each leg prefixed with (LEAGUE).
7.Reasoning:Add 1 sentence "r".
8.LISTS: Scan FULL message. Extract items 1 to N. EACH LINE IS A SEPARATE PICK. Do NOT parlay them unless it says "Parlay".

9.SPLIT PICKS: "Team +8 & ML" = 2 picks.
10.Tennis: NO "ML" on sets/games.
11.PARLAY PROPS: Expand "Player 23+ Pts" inside parlay legs.
12.SEASON: JAN/FEB is BASKETBALL (NCAAB). NCAAF is over.
13.CONFIDENCE (q): 1-10.
14.UK TYPE: Use t=UK for vague picks like "NBA EXCLUSIVE PLAY" or "WHAMMY".
15.NOISE: Remove "Early Max", "Lock".
16.PARLAY VS SEPARATE: "Leg1 + Leg2" on ONE line is a PARLAY (t=PL).
17.ODDS VALIDATION: Odds <100 (> -100) are LINES.

OUTPUT:{{"picks":[{{"i":123,"c":"Name","l":"NBA","t":"PP","p":"LeBron: Pts O 25.5","o":-110,"u":1,"r":"Found LeBron prop in OCR text"}}]}}

DATA:
{raw_data}"""


def get_compact_revision_prompt(failed_items: List[Dict[str, Any]]) -> str:
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
            "ctx": (item.get("original_text", "") or item.get("context", ""))[:600],
        }
        if item.get("pick"):
            entry["p"] = item.get("pick")
        minified.append(entry)

    items_json = json.dumps(minified, separators=(",", ":"))

    return f"""TEMP:0.1 OUTPUT:JSON(1 line)
Re-analyze failed fields using context.

TIPS:
1.c=capper at top of image/text
2.l=league from team names
3.p=pick "Team -7.5" or "Team ML"

NOISE:If p has "80K","VIP","MAX BET"->find real bet or p=null

INPUT:{items_json}

OUTPUT:[{{"i":123,"c":"Name","l":"NBA","p":"Team -5"}}]"""


def get_dsl_extraction_prompt(raw_data: str, current_date: Optional[str] = None) -> str:
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


def compress_raw_data(selected_data: List[Dict[str, Any]]) -> str:
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
