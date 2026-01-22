"""
Decoder Module - Expands compact AI responses to full field names.

This module handles the post-processing of AI responses that use the
ultra-compact schema (1-char keys, type abbreviations) and expands
them back to full field names for downstream processing.

Usage:
    from src.prompts.decoder import expand_picks_list, normalize_response
    
    # After getting AI response
    compact_picks = json.loads(response)["picks"]
    full_picks = expand_picks_list(compact_picks)
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional, Union

# =============================================================================
# EXPANSION MAPPINGS
# =============================================================================

# Compact key -> Full field name
COMPACT_TO_FULL = {
    "i": "message_id",
    "c": "capper_name",
    "l": "league",
    "t": "type",
    "p": "pick",
    "o": "odds",
    "u": "units",
    "d": "date",
    # Also support existing 2-char keys for backward compatibility
    "id": "message_id",
    "cn": "capper_name",
    "lg": "league",
    "ty": "type",
    "od": "odds",
    "dt": "date",
}

# Type abbreviation -> Full type name
TYPE_ABBREV_TO_FULL = {
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
    # Also support lowercase
    "ml": "Moneyline",
    "sp": "Spread",
    "tl": "Total",
    "pp": "Player Prop",
    "tp": "Team Prop",
    "gp": "Game Prop",
    "pd": "Period",
    "pl": "Parlay",
    "ts": "Teaser",
    "ft": "Future",
    "uk": "Unknown",
}

# Valid full type names (for passthrough)
VALID_FULL_TYPES = {
    "Moneyline", "Spread", "Total", "Player Prop", "Team Prop",
    "Game Prop", "Period", "Parlay", "Teaser", "Future", "Unknown"
}

# Valid leagues
VALID_LEAGUES = {
    "NFL", "NCAAF", "NBA", "NCAAB", "WNBA", "MLB", "NHL",
    "EPL", "MLS", "UCL", "UFC", "PFL", "TENNIS", "SOCCER",
    "EUROLEAGUE", "PGA", "F1", "Other"
}

# =============================================================================
# EXPANSION FUNCTIONS
# =============================================================================

def expand_type(type_value: Any) -> str:
    """
    Expand type abbreviation to full type name.
    
    Args:
        type_value: Type abbreviation (ML, SP, etc.) or full name
        
    Returns:
        Full type name
    """
    if not type_value:
        return "Unknown"
    
    type_str = str(type_value).strip()
    
    # Check if it's an abbreviation
    if type_str in TYPE_ABBREV_TO_FULL:
        return TYPE_ABBREV_TO_FULL[type_str]
    
    # Check if it's already a valid full type
    if type_str in VALID_FULL_TYPES:
        return type_str
    
    # Try case-insensitive match
    type_lower = type_str.lower()
    for full_type in VALID_FULL_TYPES:
        if full_type.lower() == type_lower:
            return full_type
    
    return "Unknown"


def expand_league(league_value: Any) -> str:
    """
    Validate and normalize league value.
    
    Args:
        league_value: League code
        
    Returns:
        Valid league code or "Other"
    """
    if not league_value:
        return "Other"
    
    league_str = str(league_value).strip().upper()
    
    # Direct match
    if league_str in VALID_LEAGUES:
        return league_str
    
    # Handle common variations
    league_map = {
        "NCAABB": "NCAAB",
        "CFB": "NCAAF",
        "CBB": "NCAAB",
        "PREMIER LEAGUE": "EPL",
        "CHAMPIONS LEAGUE": "UCL",
        "SERIE A": "SOCCER",
        "LA LIGA": "SOCCER",
        "BUNDESLIGA": "SOCCER",
        "LIGUE 1": "SOCCER",
    }
    
    if league_str in league_map:
        return league_map[league_str]
    
    return "Other"


def expand_compact_pick(compact: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expand a compact pick dict to full field names.
    
    Handles:
    - 1-char keys (i, c, l, t, p, o, u, d)
    - 2-char keys (id, cn, lg, ty, od, dt) for backward compat
    - Type abbreviations (ML, SP, PP, etc.)
    - Default values (units=1.0)
    
    Args:
        compact: Dict with compact keys
        
    Returns:
        Dict with full field names
    """
    if not compact or not isinstance(compact, dict):
        return {}
    
    result = {}
    
    for key, value in compact.items():
        # Get full key name
        full_key = COMPACT_TO_FULL.get(key, key)
        
        # Special handling for type field
        if full_key == "type":
            value = expand_type(value)
        
        # Special handling for league field
        elif full_key == "league":
            value = expand_league(value)
        
        # Special handling for odds (ensure int or None)
        elif full_key == "odds":
            if value is not None:
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    value = None
        
        # Special handling for units (ensure float)
        elif full_key == "units":
            try:
                value = float(value)
            except (ValueError, TypeError):
                value = 1.0
        
        result[full_key] = value
    
    # Apply defaults
    result.setdefault("units", 1.0)
    result.setdefault("capper_name", "Unknown")
    result.setdefault("league", "Other")
    result.setdefault("type", "Unknown")
    
    return result


def expand_picks_list(compact_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Expand a list of compact picks.
    
    Args:
        compact_list: List of compact pick dicts
        
    Returns:
        List of expanded pick dicts
    """
    if not compact_list or not isinstance(compact_list, list):
        return []
    
    return [expand_compact_pick(p) for p in compact_list if isinstance(p, dict)]


# =============================================================================
# RESPONSE NORMALIZATION
# =============================================================================

def extract_json_from_response(text: str) -> Optional[Union[Dict, List]]:
    """
    Extract JSON from potentially messy AI response.
    
    Handles:
    - Raw JSON
    - Markdown code blocks
    - Thinking blocks (<think>...</think>)
    - Leading/trailing text
    
    Args:
        text: Raw AI response text
        
    Returns:
        Parsed JSON (dict or list) or None
    """
    if not text:
        return None
    
    # Remove thinking blocks (DeepSeek)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = text.strip()
    
    # Try direct parse first (most efficient)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try markdown code block extraction
    if "```json" in text:
        try:
            json_str = text.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass
    
    if "```" in text:
        try:
            json_str = text.split("```")[1].split("```")[0].strip()
            return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass
    
    # Find first { or [ and try to parse from there
    for i, char in enumerate(text):
        if char in '{[':
            # Find matching closing bracket
            try:
                return json.loads(text[i:])
            except json.JSONDecodeError:
                # Try to find the end manually
                depth = 0
                end_char = '}' if char == '{' else ']'
                for j in range(i, len(text)):
                    if text[j] == char:
                        depth += 1
                    elif text[j] == end_char:
                        depth -= 1
                        if depth == 0:
                            try:
                                return json.loads(text[i:j+1])
                            except json.JSONDecodeError:
                                break
    
    return None


def normalize_response(response: str, expand: bool = True) -> List[Dict[str, Any]]:
    """
    Normalize AI response to a list of pick dicts.
    
    This is the main entry point for processing AI responses.
    It handles JSON extraction, picks array extraction, and optional expansion.
    
    Args:
        response: Raw AI response text
        expand: Whether to expand compact keys to full names (default True)
        
    Returns:
        List of pick dicts (expanded if expand=True)
    """
    if not response:
        return []
    
    # Extract JSON
    data = extract_json_from_response(response)
    
    if data is None:
        logging.warning(f"[Decoder] Failed to extract JSON from response: {response[:100]}...")
        return []
    
    # Handle different response structures
    picks = []
    
    if isinstance(data, dict):
        # Standard format: {"picks": [...]}
        if "picks" in data:
            picks = data["picks"]
        # Single pick returned as dict
        elif any(k in data for k in ["p", "pick", "i", "id"]):
            picks = [data]
        else:
            logging.warning(f"[Decoder] Unknown dict structure: {list(data.keys())}")
            return []
    elif isinstance(data, list):
        picks = data
    else:
        logging.warning(f"[Decoder] Unexpected data type: {type(data)}")
        return []
    
    if not isinstance(picks, list):
        return []
    
    # Expand if requested
    if expand:
        return expand_picks_list(picks)
    
    return picks


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================

def ensure_backward_compatible(pick: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure a pick dict has both old and new field names for transition period.
    
    This allows gradual migration of downstream code.
    
    Args:
        pick: Pick dict with either old or new field names
        
    Returns:
        Pick dict with both old and new field names
    """
    result = dict(pick)
    
    # Map new -> old for backward compat
    new_to_old = {
        "message_id": "id",
        "capper_name": "cn",
        "league": "lg",
        "type": "ty",
        "pick": "p",
        "odds": "od",
        "units": "u",
        "date": "dt",
    }
    
    for new_key, old_key in new_to_old.items():
        if new_key in result and old_key not in result:
            result[old_key] = result[new_key]
        elif old_key in result and new_key not in result:
            result[new_key] = result[old_key]
    
    return result
