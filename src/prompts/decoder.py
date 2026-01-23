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
    "r": "reasoning",
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
        expanded = expand_picks_list(picks)
        # Apply post-processing validation and correction
        return validate_and_correct_batch(expanded)
    
    return picks


# =============================================================================
# POST-PROCESSING VALIDATION & CORRECTION
# =============================================================================

# Regex patterns for type inference
SPREAD_PATTERN = re.compile(r'[+-]\d+\.?\d*(?:\s|$)')  # Team -7.5, Team +3
TOTAL_PATTERN = re.compile(r'\b(?:over|under|o|u)\s*\d+\.?\d*', re.IGNORECASE)
PLAYER_PROP_PATTERN = re.compile(r'^([A-Za-z\s\.\-\']+):\s*(\w+)\s+(over|under|o|u)\s*(\d+\.?\d*)', re.IGNORECASE)
# Player prop "Num+" format (e.g., "23+ PTS")
PLAYER_PROP_PLUS_PATTERN = re.compile(r'\d+\+\s*(?:pts?|points?|reb|rebounds?|ast|assists?|stl|steals?|blk|blocks?|3pm|threes?)', re.IGNORECASE)
PARLAY_SEPARATORS = re.compile(r'\s*[/&]\s*(?=[A-Z])')  # Separators between parlay legs (removed + to avoid "23+" false positive)
PERIOD_PATTERN = re.compile(r'\b(1H|2H|1Q|2Q|3Q|4Q|F5|F3|P1|P2|P3|First\s*Half|First\s*5)', re.IGNORECASE)
ML_EXPLICIT_PATTERN = re.compile(r'\bML\b', re.IGNORECASE)
# Parlay indicators: MLP (Moneyline Parlay), multi-leg patterns
MLP_PATTERN = re.compile(r'\bMLP\b', re.IGNORECASE)  # Moneyline Parlay
MULTI_TEAM_PATTERN = re.compile(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*[/&]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', re.IGNORECASE)  # Removed + from separators
FUTURE_PATTERN = re.compile(r'\b(Super\s*Bowl|Championship|MVP|Win\s*Total|Season|Playoff|Division)', re.IGNORECASE)


def infer_type_from_pick(pick_str: str, current_type: str) -> str:
    """
    Infer the correct bet type from the pick string.
    
    This catches misclassifications like:
    - "New Hampshire -9" classified as Moneyline (should be Spread)
    - "Lakers vs Celtics Over 220.5" classified as Spread (should be Total)
    - "LeBron: Pts Over 25.5" classified as Moneyline (should be Player Prop)
    - "De Minaur/Warriors MLP" classified as Moneyline (should be Parlay)
    
    Args:
        pick_str: The pick string (e.g., "Chiefs -7.5")
        current_type: The type assigned by AI
        
    Returns:
        Corrected type if inference is confident, else original
    """
    if not pick_str:
        return current_type
    
    pick_str = pick_str.strip()
    
    # Priority 0: Futures (Super Bowl, Championship, etc.)
    if FUTURE_PATTERN.search(pick_str):
        return "Future"
    
    # Priority 1: Period bets (check first as they may contain spreads/totals)
    if PERIOD_PATTERN.search(pick_str):
        return "Period"
    
    # Priority 2: Player Prop with "Num+ STAT" format (e.g., "23+ PTS")
    # Check this BEFORE parlay detection to avoid "+" being treated as separator
    if PLAYER_PROP_PLUS_PATTERN.search(pick_str):
        return "Player Prop"
    
    # Priority 3: MLP = Moneyline Parlay (explicit parlay marker)
    if MLP_PATTERN.search(pick_str):
        return "Parlay"
    
    # Priority 4: Multiple teams joined by / & (parlay pattern)
    # e.g., "Youngstown St. & St. Thomas", "De Minaur/Warriors"
    if MULTI_TEAM_PATTERN.search(pick_str):
        # Check if it's actually a "Team A vs Team B" total
        if not TOTAL_PATTERN.search(pick_str):
            return "Parlay"
    
    # Priority 5: Parlay detection (multiple legs separated by / &)
    if len(PARLAY_SEPARATORS.split(pick_str)) > 1:
        return "Parlay"
    
    # Priority 6: Explicit ML marker - trust it
    if ML_EXPLICIT_PATTERN.search(pick_str):
        # Only if no spread number follows "ML"
        after_ml = pick_str.split('ML')[-1].strip()
        if not SPREAD_PATTERN.match(after_ml):
            return "Moneyline"
    
    # Priority 7: Player/Team Prop format (Name: Stat Over/Under X)
    if PLAYER_PROP_PATTERN.search(pick_str):
        return "Player Prop"
    
    # Priority 8: Total (Over/Under pattern with no specific team indicator after)
    if TOTAL_PATTERN.search(pick_str):
        # Check if it looks like "Team vs Team Over X" or just "Over X"
        if 'vs' in pick_str.lower() or ' @ ' in pick_str:
            return "Total"
        # Could be a player prop if it has a name before
        if ':' in pick_str:
            return "Player Prop"
        return "Total"
    
    # Priority 9: Spread detection (Team +/-X.X without ML)
    # This catches the critical "Team -9" -> Moneyline error
    if SPREAD_PATTERN.search(pick_str):
        # Make sure it's not "Team ML -110" (odds following ML)
        if not ML_EXPLICIT_PATTERN.search(pick_str):
            return "Spread"
    
    return current_type


def normalize_pick_format(pick_str: str, bet_type: str) -> str:
    """
    Normalize pick string to match rubric format.
    
    Fixes:
    - "LAKERS/CLIPPERS" -> "Lakers vs Clippers"
    - "U 221.5" -> "Under 221.5"
    - "Luka Doncic 23+ PTS" -> "Luka Doncic: Pts Over 22.5"
    - "De Minaur/Warriors MLP" -> "De Minaur ML / Warriors ML"
    
    Args:
        pick_str: Original pick string
        bet_type: The (corrected) bet type
        
    Returns:
        Normalized pick string
    """
    if not pick_str:
        return pick_str
    
    result = pick_str.strip()
    
    # PRIORITY 1: Normalize Player Props FIRST (before any + replacement)
    # This prevents "23+" from being treated as a parlay separator
    if bet_type == "Player Prop":
        # Pattern 1: Name Num+ STAT (e.g., "Luka Doncic 23+ PTS")
        plus_pattern = re.compile(r'^([A-Za-z\s\.\-\']+?)\s+(\d+)\+\s*(\w+)$', re.IGNORECASE)
        match = plus_pattern.match(result)
        if match:
            name, num, stat = match.groups()
            # Convert 23+ to Over 22.5
            over_line = float(num) - 0.5
            result = f"{name.strip()}: {stat.capitalize()} Over {over_line}"
        else:
            # Pattern 2: Name STAT Num+ (e.g., "LeBron Points 25+")
            alt_pattern = re.compile(r'^([A-Za-z\s\.\-\']+?)\s+(\w+)\s+(\d+)\+$', re.IGNORECASE)
            match = alt_pattern.match(result)
            if match:
                name, stat, num = match.groups()
                over_line = float(num) - 0.5
                result = f"{name.strip()}: {stat.capitalize()} Over {over_line}"
    
    # Normalize Over/Under abbreviations (handle edge cases)
    result = re.sub(r'\bO\s+(\d)', r'Over \1', result, flags=re.IGNORECASE)
    result = re.sub(r'\bU\s+(\d)', r'Under \1', result, flags=re.IGNORECASE)
    # Also handle "o221.5" without space
    result = re.sub(r'\bo(\d+\.?\d*)\b', r'Over \1', result, flags=re.IGNORECASE)
    result = re.sub(r'\bu(\d+\.?\d*)\b', r'Under \1', result, flags=re.IGNORECASE)
    
    # Normalize team separators for Totals
    if bet_type == "Total":
        # Replace "/" or "&" between teams with "vs"
        result = re.sub(r'([A-Za-z]+)\s*[/&]\s*([A-Za-z]+)', r'\1 vs \2', result)
    
    # Normalize Parlays: Expand MLP to "ML / ML" format
    if bet_type == "Parlay":
        # Handle "Team1/Team2 MLP" -> "Team1 ML / Team2 ML"
        mlp_match = re.search(r'^(.+?)\s*MLP\s*$', result, re.IGNORECASE)
        if mlp_match:
            teams_part = mlp_match.group(1)
            # Split by / + &
            teams = re.split(r'\s*[/+&]\s*', teams_part)
            if len(teams) > 1:
                result = ' / '.join([f"{t.strip()} ML" for t in teams])
        else:
            # Ensure parlay legs are separated by " / "
            result = re.sub(r'\s*[+&]\s*', ' / ', result)
    
    # Title case team names (if all caps)
    words = result.split()
    normalized_words = []
    preserve_uppercase = {'ML', 'PTS', 'REB', 'AST', 'NFL', 'NBA', 'NHL', 'MLB', 'UFC', 'PRA', 'SOG', 'MLP'}
    for word in words:
        if word.isupper() and len(word) > 2 and word not in preserve_uppercase:
            normalized_words.append(word.title())
        else:
            normalized_words.append(word)
    result = ' '.join(normalized_words)
    
    return result


def extract_structured_fields(pick: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured fields from pick string based on type.
    
    For Spreads: Extracts 'line' (-7.5)
    For Totals: Extracts total number
    For Props: Extracts 'subject' (player), 'market' (stat), 'line', 'prop_side'
    
    Args:
        pick: Pick dict with 'pick' and 'type' fields
        
    Returns:
        Pick dict with additional structured fields populated
    """
    result = dict(pick)
    pick_str = result.get('pick', '')
    bet_type = result.get('type', 'Unknown')
    
    if not pick_str:
        return result
    
    # Extract spread line
    if bet_type == "Spread":
        spread_match = re.search(r'([+-]\d+\.?\d*)', pick_str)
        if spread_match:
            try:
                result['line'] = float(spread_match.group(1))
            except ValueError:
                pass
    
    # Extract total line
    elif bet_type == "Total":
        total_match = re.search(r'(?:over|under|o|u)\s*(\d+\.?\d*)', pick_str, re.IGNORECASE)
        if total_match:
            try:
                result['line'] = float(total_match.group(1))
            except ValueError:
                pass
        # Extract side
        if re.search(r'\bover\b', pick_str, re.IGNORECASE):
            result['prop_side'] = 'Over'
        elif re.search(r'\bunder\b', pick_str, re.IGNORECASE):
            result['prop_side'] = 'Under'
    
    # Extract player prop fields
    elif bet_type == "Player Prop":
        prop_match = PLAYER_PROP_PATTERN.search(pick_str)
        if prop_match:
            result['subject'] = prop_match.group(1).strip()
            result['market'] = prop_match.group(2).capitalize()
            side = prop_match.group(3).lower()
            result['prop_side'] = 'Over' if side in ('over', 'o') else 'Under'
            try:
                result['line'] = float(prop_match.group(4))
            except ValueError:
                pass
    
    return result


def validate_and_correct_pick(pick: Dict[str, Any]) -> Dict[str, Any]:
    """
    Full post-processing validation and correction for a single pick.
    
    1. Infers correct type from pick string
    2. Normalizes pick format
    3. Extracts structured fields
    
    Args:
        pick: Expanded pick dict
        
    Returns:
        Validated and corrected pick dict
    """
    if not pick or not isinstance(pick, dict):
        return pick
    
    result = dict(pick)
    pick_str = result.get('pick', '')
    current_type = result.get('type', 'Unknown')
    
    # Step 1: Infer correct type
    corrected_type = infer_type_from_pick(pick_str, current_type)
    if corrected_type != current_type:
        logging.debug(f"[Decoder] Type correction: '{current_type}' -> '{corrected_type}' for pick: {pick_str[:50]}")
        result['type'] = corrected_type
    
    # Step 2: Normalize format
    normalized_pick = normalize_pick_format(pick_str, corrected_type)
    if normalized_pick != pick_str:
        result['pick'] = normalized_pick
    
    # Step 3: Extract structured fields
    result = extract_structured_fields(result)
    
    return result


def validate_and_correct_batch(picks: List[Dict[str, Any]], valid_message_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    """
    Apply post-processing validation to a batch of picks.
    
    Args:
        picks: List of expanded pick dicts
        valid_message_ids: Optional list of message IDs that were in the input batch.
                          If provided, picks with non-matching IDs are filtered out
                          to prevent cross-contamination/hallucination.
        
    Returns:
        List of validated and corrected pick dicts
    """
    validated = [validate_and_correct_pick(p) for p in picks]
    
    # Filter out picks with invalid message IDs (prevents hallucination)
    if valid_message_ids:
        valid_set = set(valid_message_ids)
        before_count = len(validated)
        validated = [p for p in validated if p.get('message_id') in valid_set]
        if len(validated) < before_count:
            filtered_count = before_count - len(validated)
            logging.warning(f"[Decoder] Filtered {filtered_count} picks with invalid message_ids (cross-contamination prevention)")
    
    return validated


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
