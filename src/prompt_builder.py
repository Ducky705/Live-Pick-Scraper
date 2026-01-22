"""
Prompt Builder - Generates optimized prompts for betting pick extraction.

This module has been optimized for maximum token efficiency:
- 1-char JSON keys in output (i, c, l, t, p, o, u)
- Type abbreviations (ML, SP, PP, etc.)
- Compressed formatting rules
- ~67% reduction in prompt tokens

The decoder module (src.prompts.decoder) expands compact responses back to full field names.
"""

import json
from datetime import datetime
from src.utils import clean_text_for_ai

# Import from centralized prompts module
from src.prompts.core import (
    SCHEMA_DOC,
    PICK_FORMAT_RULES,
    NOISE_FILTER,
    get_compact_extraction_prompt,
    get_compact_revision_prompt,
    compress_raw_data,
)


def get_master_formatting_guide():
    """
    DEPRECATED: Returns compressed formatting guide.
    
    Kept for backward compatibility. New code should use 
    get_compact_extraction_prompt() from src.prompts.core instead.
    
    Original: ~100 lines of Markdown tables
    New: ~15 lines of compressed rules
    """
    return f"""
{SCHEMA_DOC}
{PICK_FORMAT_RULES}
{NOISE_FILTER}
"""


def generate_ai_prompt(selected_data):
    """
    Generate ultra-compact extraction prompt.
    
    Token reduction: ~67% (from ~1200 to ~400 tokens)
    
    Args:
        selected_data: List of message dicts with id, text, ocr_texts
        
    Returns:
        Compact prompt string ready for AI
    """
    # Compress input data
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

    # Ultra-compact prompt (~400 tokens vs original ~1200)
    prompt = f"""TEMP:0 OUTPUT:JSON(1 line,no markdown)
Extract betting picks from data below.

KEYS:i=id,c=capper,l=league,t=type,p=pick,o=odds,u=units
TYPES:ML=Moneyline,SP=Spread,TL=Total,PP=Player Prop,TP=Team Prop,GP=Game Prop,PD=Period,PL=Parlay,TS=Teaser,FT=Future,UK=Unknown
LEAGUES:NFL,NCAAF,NBA,NCAAB,WNBA,MLB,NHL,EPL,MLS,UCL,UFC,PFL,TENNIS,SOCCER,PGA,F1,Other

PICK FORMATS:
ML=Team ML|SP=Team -7.5|TL=Team A vs B O/U X
PP=Name: Stat O/U X|TP=Team: Stat O/U X|GP=Desc: Value
PD=1H/1Q/F5 + bet format|PL=(LG) Leg1 / (LG) Leg2|FT=Event: Selection
TENNIS:Name ML|Name +/-X sets|Name +/-X games|A vs B O/U X games
PERIOD TRIGGERS:1H,2H,1Q,2Q,3Q,4Q,F5,F3,P1,P2,P3,"First Half","First 5"
STATS:Pts,Reb,Ast,PRA,PassYds,RushYds,RecYds,PassTD,Rec,K,H,HR,RBI,SOG,G,A

SKIP:VIP,WHALE,MAX BET,LOCK,80K,GUARANTEED,@cappersfree,@watermarks,records,sportsbook names

RULES:
1.c=capper from header/username,NOT watermarks(@cappersfree,capperstree)
2.o=American odds int(-110,+150) or null if not visible.DO NOT GUESS
3.u=units float,default 1."80K MAIN PLAY"=u:80000,not pick
4.Separate picks per capper
5.Period:if text has 1H/1Q/F5/First Half/etc,t=PD
6.Parlay:each leg prefixed with (LEAGUE)
7.Valid pick needs:team/player name + bet(-7.5,ML,Over 215)

OUTPUT:{{"picks":[{{"i":123,"c":"Name","l":"NBA","t":"PP","p":"LeBron: Pts O 25.5","o":-110,"u":1}}]}}

DATA:
{full_raw_data}"""
    
    return prompt


def generate_revision_prompt(failed_items):
    """
    Generate compact refinement prompt for failed extractions.
    
    Uses MINIFIED keys for both input and output efficiency.
    
    Args:
        failed_items: List of items with failed fields
        
    Returns:
        Compact revision prompt
    """
    items_detail = []
    for item in failed_items:
        # Minify keys for input
        detail = {
            "i": item.get("message_id"),
            "fails": [],
            "vals": {},
            "ctx": clean_text_for_ai(item.get("original_text", ""))[:600]
        }
        
        # Identify specifically what's wrong
        if item.get("capper_name") in ["Unknown", "N/A", None, ""]:
            detail["fails"].append("c")
            detail["vals"]["c"] = "Unknown"
        if item.get("league") in ["Unknown", "Other", None, ""]:
            detail["fails"].append("l")
            detail["vals"]["l"] = item.get("league", "Unknown")
        if not item.get("pick") or item.get("pick") == "Unknown" or True: 
            detail["fails"].append("p")
            detail["vals"]["p"] = item.get("pick", "Unknown")
            
        items_detail.append(detail)
    
    items_json = json.dumps(items_detail, indent=None, separators=(',', ':'))
    
    return f"""TEMP:0.1 OUTPUT:JSON(1 line)
Re-analyze failed fields using context(ctx).

TIPS:
1.c=capper at top of image/text,NOT watermarks
2.l=league from team names(NFL,NBA,MLB,etc)
3.p=pick "Team -7.5" or "Team ML"

NOISE:If p has "80K","VIP","MAX BET"->find real bet or p=null

INPUT:{items_json}

OUTPUT:[{{"i":123,"c":"Name","l":"NBA","p":"Team -5"}}]"""


def generate_smart_fill_prompt(unknown_items):
    """
    Generate compact prompt for filling unknown capper names.
    
    Args:
        unknown_items: List of items with unknown cappers
        
    Returns:
        Compact smart fill prompt
    """
    # Minified Input
    minified = []
    for item in unknown_items:
        minified.append({
            "i": item.get("message_id"),
            "p": item.get("pick"),
            "ctx": clean_text_for_ai(item.get("context", ""))[:400]
        })
        
    items_json = json.dumps(minified, separators=(',', ':'))
    
    return f"""TEMP:0.1 OUTPUT:JSON(1 line)
Find capper name(c) from context.

INPUT:{items_json}

OUTPUT:[{{"i":123,"c":"FoundName"}}]"""


# =============================================================================
# BACKWARD COMPATIBILITY EXPORTS
# =============================================================================

# These functions are kept for code that imports them directly
__all__ = [
    'get_master_formatting_guide',
    'generate_ai_prompt', 
    'generate_revision_prompt',
    'generate_smart_fill_prompt',
]
