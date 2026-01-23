"""
Core Prompt Components - Centralized definitions for maximum token efficiency.

This module contains:
- Compact schema mappings (1-char keys)
- Type abbreviations
- League codes
- Prompt builder functions

IMPORTANT: All prompts use ultra-compact output format to minimize AI output tokens.
The decoder.py module expands these back to full field names.
"""

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
    "NFL", "NCAAF", "NBA", "NCAAB", "WNBA", "MLB", "NHL",
    "EPL", "MLS", "UCL", "UFC", "PFL", "TENNIS", "SOCCER",
    "EUROLEAGUE", "PGA", "F1", "Other"
]

# Noise keywords to skip (marketing, watermarks, etc.)
NOISE_KEYWORDS = [
    "VIP", "WHALE", "MAX BET", "LOCK", "80K", "GUARANTEED",
    "@cappersfree", "@freepicks", "@vippicks", "POTD",
    "Join", "DM for", "FREE PLAY"
]

# Stat abbreviations for props
STAT_ABBREVS = {
    # Basketball
    "Pts": "Points", "Reb": "Rebounds", "Ast": "Assists", 
    "Blk": "Blocks", "Stl": "Steals", "3PM": "3-Pointers Made",
    "PRA": "Pts+Reb+Ast",
    # Football
    "PassYds": "Passing Yards", "RushYds": "Rushing Yards",
    "RecYds": "Receiving Yards", "PassTD": "Passing TDs",
    "Rec": "Receptions", "Comp": "Completions",
    # Baseball
    "K": "Strikeouts", "H": "Hits", "HR": "Home Runs",
    "RBI": "RBIs", "TotalBases": "Total Bases",
    # Hockey
    "SOG": "Shots on Goal", "G": "Goals", "A": "Assists", "P": "Points",
}

# =============================================================================
# COMPRESSED PROMPT FRAGMENTS
# =============================================================================

# Ultra-compact schema doc for prompts (~150 chars vs ~800 original)
SCHEMA_DOC = """KEYS:i=id,c=capper(Use text header/username first),l=league,t=type,p=pick,o=odds(int,e.g.-110),u=units(float)
TYPES:ML,SP,TL,PP,TP,GP,PD,PL,TS,FT,UK
LEAGUES:NFL,NCAAF,NBA,NCAAB,WNBA,MLB,NHL,EPL,MLS,UCL,UFC,PFL,TENNIS,SOCCER,PGA,F1,Other"""

# Pick format rules (compressed from 100+ line formatting guide)
PICK_FORMAT_RULES = """PICK FORMATS:
ML=Team ML|SP=Team -7.5|TL=Team A vs B O/U X
PP=Name: Stat O/U X|TP=Team: Stat O/U X|GP=Desc: Value
PD=1H/1Q/F5 + bet format|PL=(LG) Leg1 / (LG) Leg2|FT=Event: Selection
TENNIS:Name ML|Name +/-X sets|Name +/-X games|A vs B O/U X games
PERIOD TRIGGERS:1H,2H,1Q,2Q,3Q,4Q,F5,F3,P1,P2,P3,"First Half","First 5"
STATS:Pts,Reb,Ast,PRA,PassYds,RushYds,RecYds,PassTD,Rec,K,H,HR,RBI,SOG,G,A

CRITICAL TYPE RULES:
-If pick has "Team -7" or "Team +3.5" (number after team): t=SP (Spread), NOT ML
-If pick has "ML" explicitly: t=ML
-If pick has "Team A / Team B" or "+" between teams: t=PL (Parlay)
-If pick has "Over X" or "Under X" with two teams: t=TL (Total)
-Parlay 1, Parlay 2, etc. are SEPARATE picks with t=PL"""

# Noise filter instruction
NOISE_FILTER = """SKIP:VIP,WHALE,MAX BET,LOCK,80K,GUARANTEED,@watermarks,records,sportsbook names,recaps with checkmarks"""

# Negative constraints (new)
NEGATIVE_CONSTRAINTS = """CONSTRAINTS:
1.DO NOT use "80K", "VIP", "MAX" as picks. These are noise.
2.DO NOT use "@cappersfree" or watermarks as capper name.
3.If "80K" is present, u=80000.
4.If no clear bet, p=null.
5.CRITICAL: Each pick MUST use the exact "i" (message_id) from its source message.
  DO NOT mix picks between messages. Only output picks found in each specific message."""

# =============================================================================
# PROMPT BUILDER FUNCTIONS
# =============================================================================

def get_compact_extraction_prompt(raw_data: str, current_date: Optional[str] = None) -> str:
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
1.c=capper from header/username,NOT watermarks(@cappersfree,capperstree)
2.o=American odds int(-110,+150) or null if not visible
3.u=units float,default 1. "80K"=80000 units
4.Separate picks per capper
5.Period bets:if text has 1H/1Q/F5/etc,t=PD
6.Parlay:each leg prefixed with (LEAGUE)
7.Reasoning:Add 1 sentence "r" field explaining why it is a valid pick.

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
            "ctx": (item.get("original_text", "") or item.get("context", ""))[:600]
        }
        if item.get("pick"):
            entry["p"] = item.get("pick")
        minified.append(entry)
    
    items_json = json.dumps(minified, separators=(',', ':'))
    
    return f"""TEMP:0.1 OUTPUT:JSON(1 line)
Re-analyze failed fields using context.

TIPS:
1.c=capper at top of image/text
2.l=league from team names
3.p=pick "Team -7.5" or "Team ML"

NOISE:If p has "80K","VIP","MAX BET"->find real bet or p=null

INPUT:{items_json}

OUTPUT:[{{"i":123,"c":"Name","l":"NBA","p":"Team -5"}}]"""


def get_compact_ocr_batch_prompt(n: int) -> str:
    """
    Generate ultra-compact OCR batch prompt.
    
    Token reduction: ~70% (from ~100 to ~30 tokens)
    
    Args:
        n: Number of images in batch
        
    Returns:
        Compact OCR batch prompt
    """
    return f"Extract text from {n} images. Return JSON array of {n} strings:[\"text1\",\"text2\"]. Combine each image's text into 1 string with \\n. No markdown."


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
5.l=specific league if inferable
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
        
        text = clean_text_for_ai(item.get('text', ''))
        ocr_texts = item.get('ocr_texts', [])
        
        # Fallback to legacy field
        if not ocr_texts and item.get('ocr_text'):
            ocr_texts = [item.get('ocr_text')]
        
        if text:
            entry += f" [T] {text}"
        
        for i, ocr in enumerate(ocr_texts):
            cleaned = clean_text_for_ai(ocr)
            if cleaned:
                entry += f" [OCR {i+1}] {cleaned}"
        
        lines.append(entry)
    
    return "\n".join(lines)
