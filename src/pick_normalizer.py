# src/pick_normalizer.py
"""
Post-extraction pick normalization.

Implements the recommendations from benchmark report v2:
1. Period indicator standardization (1H, 2H, Q1, etc.)
2. Team name normalization (abbreviations to full names)
3. Case normalization and formatting consistency
"""

import re
from typing import Optional

# =============================================================================
# PERIOD INDICATOR NORMALIZATION
# =============================================================================

# Maps various period formats to canonical form
PERIOD_ALIASES = {
    # First Half
    "1h": "1H",
    "first half": "1H",
    "1st half": "1H",
    "firsthalf": "1H",
    "fh": "1H",
    "h1": "1H",
    
    # Second Half
    "2h": "2H",
    "second half": "2H",
    "2nd half": "2H",
    "secondhalf": "2H",
    "sh": "2H",
    "h2": "2H",
    
    # Quarters
    "1q": "1Q",
    "first quarter": "1Q",
    "1st quarter": "1Q",
    "q1": "1Q",
    
    "2q": "2Q",
    "second quarter": "2Q",
    "2nd quarter": "2Q",
    "q2": "2Q",
    
    "3q": "3Q",
    "third quarter": "3Q",
    "3rd quarter": "3Q",
    "q3": "3Q",
    
    "4q": "4Q",
    "fourth quarter": "4Q",
    "4th quarter": "4Q",
    "q4": "4Q",
    
    # Hockey Periods
    "1p": "1P",
    "first period": "1P",
    "1st period": "1P",
    "p1": "1P",
    
    "2p": "2P",
    "second period": "2P",
    "2nd period": "2P",
    "p2": "2P",
    
    "3p": "3P",
    "third period": "3P",
    "3rd period": "3P",
    "p3": "3P",
    
    # Baseball Innings
    "f5": "F5",
    "first 5": "F5",
    "first five": "F5",
    "first 5 innings": "F5",
    "first5": "F5",
    "1st 5": "F5",
    
    "f3": "F3",
    "first 3": "F3",
    "first three": "F3",
    "1st 3": "F3",
    
    "f1": "F1",
    "first inning": "F1",
    "1st inning": "F1",
}

# =============================================================================
# TEAM NAME NORMALIZATION
# =============================================================================

# Common abbreviations mapped to standard names
# Keys are lowercase for case-insensitive matching
TEAM_ALIASES = {
    # NBA
    "lal": "Lakers",
    "lac": "Clippers",
    "la lakers": "Lakers",
    "la clippers": "Clippers",
    "los angeles lakers": "Lakers",
    "los angeles clippers": "Clippers",
    "gs": "Warriors",
    "gsw": "Warriors",
    "golden state": "Warriors",
    "golden state warriors": "Warriors",
    "ny": "Knicks",
    "nyk": "Knicks",
    "new york knicks": "Knicks",
    "bkn": "Nets",
    "brooklyn": "Nets",
    "brooklyn nets": "Nets",
    "phx": "Suns",
    "phoenix": "Suns",
    "phoenix suns": "Suns",
    "sa": "Spurs",
    "sas": "Spurs",
    "san antonio": "Spurs",
    "san antonio spurs": "Spurs",
    "okc": "Thunder",
    "oklahoma city": "Thunder",
    "oklahoma city thunder": "Thunder",
    "no": "Pelicans",
    "nop": "Pelicans",
    "new orleans": "Pelicans",
    "new orleans pelicans": "Pelicans",
    "dal": "Mavericks",
    "dallas": "Mavericks",
    "dallas mavericks": "Mavericks",
    "mavs": "Mavericks",
    "hou": "Rockets",
    "houston": "Rockets",
    "houston rockets": "Rockets",
    "mem": "Grizzlies",
    "memphis": "Grizzlies",
    "memphis grizzlies": "Grizzlies",
    "min": "Timberwolves",
    "minnesota": "Timberwolves",
    "wolves": "Timberwolves",
    "den": "Nuggets",
    "denver": "Nuggets",
    "denver nuggets": "Nuggets",
    "por": "Trail Blazers",
    "portland": "Trail Blazers",
    "blazers": "Trail Blazers",
    "uta": "Jazz",
    "utah": "Jazz",
    "utah jazz": "Jazz",
    "sac": "Kings",
    "sacramento": "Kings",
    "sacramento kings": "Kings",
    "bos": "Celtics",
    "boston": "Celtics",
    "boston celtics": "Celtics",
    "phi": "76ers",
    "philly": "76ers",
    "philadelphia": "76ers",
    "sixers": "76ers",
    "tor": "Raptors",
    "toronto": "Raptors",
    "toronto raptors": "Raptors",
    "chi": "Bulls",
    "chicago": "Bulls",
    "chicago bulls": "Bulls",
    "cle": "Cavaliers",
    "cleveland": "Cavaliers",
    "cavs": "Cavaliers",
    "det": "Pistons",
    "detroit": "Pistons",
    "detroit pistons": "Pistons",
    "ind": "Pacers",
    "indiana": "Pacers",
    "indiana pacers": "Pacers",
    "mil": "Bucks",
    "milwaukee": "Bucks",
    "milwaukee bucks": "Bucks",
    "atl": "Hawks",
    "atlanta": "Hawks",
    "atlanta hawks": "Hawks",
    "cha": "Hornets",
    "charlotte": "Hornets",
    "charlotte hornets": "Hornets",
    "mia": "Heat",
    "miami": "Heat",
    "miami heat": "Heat",
    "orl": "Magic",
    "orlando": "Magic",
    "orlando magic": "Magic",
    "wsh": "Wizards",
    "was": "Wizards",
    "washington": "Wizards",
    "washington wizards": "Wizards",
    
    # NFL
    "kc": "Chiefs",
    "kansas city": "Chiefs",
    "kansas city chiefs": "Chiefs",
    "buf": "Bills",
    "buffalo": "Bills",
    "buffalo bills": "Bills",
    "gb": "Packers",
    "green bay": "Packers",
    "green bay packers": "Packers",
    "sf": "49ers",
    "san francisco": "49ers",
    "niners": "49ers",
    "sea": "Seahawks",
    "seattle": "Seahawks",
    "seattle seahawks": "Seahawks",
    "ari": "Cardinals",
    "arizona": "Cardinals",
    "az cards": "Cardinals",
    "bal": "Ravens",
    "baltimore": "Ravens",
    "baltimore ravens": "Ravens",
    "pit": "Steelers",
    "pittsburgh": "Steelers",
    "pittsburgh steelers": "Steelers",
    "cin": "Bengals",
    "cincinnati": "Bengals",
    "cincinnati bengals": "Bengals",
    "ten": "Titans",
    "tennessee": "Titans",
    "tennessee titans": "Titans",
    "jax": "Jaguars",
    "jacksonville": "Jaguars",
    "jaguars": "Jaguars",
    "ne": "Patriots",
    "new england": "Patriots",
    "patriots": "Patriots",
    "pats": "Patriots",
    "nyj": "Jets",
    "new york jets": "Jets",
    "nyg": "Giants",
    "new york giants": "Giants",
    "car": "Panthers",
    "carolina": "Panthers",
    "carolina panthers": "Panthers",
    "tb": "Buccaneers",
    "tampa bay": "Buccaneers",
    "bucs": "Buccaneers",
    "no saints": "Saints",
    "new orleans saints": "Saints",
    "lv": "Raiders",
    "las vegas": "Raiders",
    "raiders": "Raiders",
    "lac chargers": "Chargers",
    "la chargers": "Chargers",
    "lar": "Rams",
    "la rams": "Rams",
    
    # NHL
    "vgk": "Golden Knights",
    "vegas": "Golden Knights",
    "col": "Avalanche",
    "colorado": "Avalanche",
    "avs": "Avalanche",
    "edm": "Oilers",
    "edmonton": "Oilers",
    "edmonton oilers": "Oilers",
    "cgy": "Flames",
    "calgary": "Flames",
    "calgary flames": "Flames",
    "van": "Canucks",
    "vancouver": "Canucks",
    "vancouver canucks": "Canucks",
    "wpg": "Jets",
    "winnipeg": "Jets",
    "winnipeg jets": "Jets",
    "ott": "Senators",
    "ottawa": "Senators",
    "ottawa senators": "Senators",
    "mtl": "Canadiens",
    "montreal": "Canadiens",
    "habs": "Canadiens",
    "fla": "Panthers",
    "florida": "Panthers",
    "florida panthers": "Panthers",
    "tbl": "Lightning",
    "tampa": "Lightning",
    "tampa bay lightning": "Lightning",
    "nyr": "Rangers",
    "ny rangers": "Rangers",
    "nyi": "Islanders",
    "ny islanders": "Islanders",
    "njd": "Devils",
    "nj": "Devils",
    "new jersey": "Devils",
    "cbj": "Blue Jackets",
    "columbus": "Blue Jackets",
    "stl": "Blues",
    "st louis": "Blues",
    "st. louis": "Blues",
    "nsh": "Predators",
    "nashville": "Predators",
    "preds": "Predators",
    "ana": "Ducks",
    "anaheim": "Ducks",
    "anaheim ducks": "Ducks",
    "sjc": "Sharks",
    "sj": "Sharks",
    "san jose": "Sharks",
    
    # MLB
    "lad": "Dodgers",
    "la dodgers": "Dodgers",
    "los angeles dodgers": "Dodgers",
    "sdp": "Padres",
    "sd": "Padres",
    "san diego": "Padres",
    "nym": "Mets",
    "ny mets": "Mets",
    "new york mets": "Mets",
    "nyy": "Yankees",
    "ny yankees": "Yankees",
    "new york yankees": "Yankees",
    "tex": "Rangers",
    "texas": "Rangers",
    "texas rangers": "Rangers",
    "cws": "White Sox",
    "white sox": "White Sox",
    "chw": "White Sox",
    "chc": "Cubs",
    "chicago cubs": "Cubs",
    "stl cards": "Cardinals",
    "st louis cardinals": "Cardinals",
    
    # NCAAB / NCAAF common abbreviations
    "unc": "North Carolina",
    "duke": "Duke",
    "uk": "Kentucky",
    "osu": "Ohio State",
    "msu": "Michigan State",
    "usc": "USC",
    "ucla": "UCLA",
    "ou": "Oklahoma",
    "ut": "Texas",
    "tcu": "TCU",
    "lsu": "LSU",
    "uga": "Georgia",
    "bama": "Alabama",
    "dav": "Davidson",
    "cincy": "Cincinnati",
    "pitt": "Pittsburgh",
    "cuse": "Syracuse",
    "uva": "Virginia",
    "vt": "Virginia Tech",
    "wvu": "West Virginia",
    "ariz st": "Arizona State",
    "asu": "Arizona State",
    "az st": "Arizona State",
    "mizzou": "Missouri",
    "ark": "Arkansas",
    "miss": "Ole Miss",
    "ole miss": "Ole Miss",
    "miss st": "Mississippi State",
    "msst": "Mississippi State",
}


def normalize_period_indicator(pick_text: str) -> str:
    """
    Normalizes period indicators in a pick text to canonical format.
    
    Examples:
        "1h NYK vs BOS Over 110" -> "1H NYK vs BOS Over 110"
        "First Half Lakers -3" -> "1H Lakers -3"
        "Over 1H 110" -> "1H Over 110"
    """
    if not pick_text:
        return pick_text
    
    result = pick_text
    
    # Sort by length descending to match longer phrases first
    for alias, canonical in sorted(PERIOD_ALIASES.items(), key=lambda x: -len(x[0])):
        # Case-insensitive match with word boundaries
        pattern = rf'\b{re.escape(alias)}\b'
        result = re.sub(pattern, canonical, result, flags=re.IGNORECASE)
    
    return result


def normalize_team_name(pick_text: str) -> str:
    """
    Normalizes team abbreviations to their standard names.
    
    Examples:
        "LAL -5" -> "Lakers -5"
        "Golden State Warriors ML" -> "Warriors ML"
        "DAV +3" -> "Davidson +3"
    """
    if not pick_text:
        return pick_text
    
    result = pick_text
    
    # Sort by length descending to match longer names first
    for alias, canonical in sorted(TEAM_ALIASES.items(), key=lambda x: -len(x[0])):
        # Case-insensitive match with word boundaries
        pattern = rf'\b{re.escape(alias)}\b'
        result = re.sub(pattern, canonical, result, flags=re.IGNORECASE)
    
    return result


def normalize_over_under(pick_text: str) -> str:
    """
    Standardizes over/under notation.
    
    Examples:
        "o215.5" -> "Over 215.5"
        "u48" -> "Under 48"
        "OVER 110" -> "Over 110"
    """
    if not pick_text:
        return pick_text
    
    result = pick_text
    
    # Normalize "o" and "u" prefixes for totals
    result = re.sub(r'\bo(\d+\.?\d*)', r'Over \1', result, flags=re.IGNORECASE)
    result = re.sub(r'\bu(\d+\.?\d*)', r'Under \1', result, flags=re.IGNORECASE)
    
    # Standardize case for Over/Under
    result = re.sub(r'\bover\b', 'Over', result, flags=re.IGNORECASE)
    result = re.sub(r'\bunder\b', 'Under', result, flags=re.IGNORECASE)
    
    return result


def normalize_moneyline(pick_text: str) -> str:
    """
    Standardizes moneyline notation.
    
    Examples:
        "Lakers ml" -> "Lakers ML"
        "Chiefs Moneyline" -> "Chiefs ML"
    """
    if not pick_text:
        return pick_text
    
    result = pick_text
    
    # Normalize moneyline to ML
    result = re.sub(r'\bmoneyline\b', 'ML', result, flags=re.IGNORECASE)
    result = re.sub(r'\bml\b', 'ML', result, flags=re.IGNORECASE)
    
    return result


def normalize_spread(pick_text: str) -> str:
    """
    Ensures consistent spread formatting.
    
    Examples:
        "Lakers - 5.5" -> "Lakers -5.5"
        "Chiefs +3.0" -> "Chiefs +3"
    """
    if not pick_text:
        return pick_text
    
    result = pick_text
    
    # Remove space between sign and number
    result = re.sub(r'([+-])\s+(\d)', r'\1\2', result)
    
    # Remove trailing .0 from whole numbers
    result = re.sub(r'(\d+)\.0\b', r'\1', result)
    
    return result


def normalize_whitespace(pick_text: str) -> str:
    """Normalizes whitespace in pick text."""
    if not pick_text:
        return pick_text
    
    # Collapse multiple spaces
    result = re.sub(r'\s+', ' ', pick_text)
    
    # Trim
    result = result.strip()
    
    return result


def normalize_pick(pick_text: str) -> str:
    """
    Applies all normalization rules to a pick text.
    
    This is the main entry point for pick normalization.
    """
    if not pick_text:
        return pick_text
    
    result = pick_text
    
    # Apply normalizations in order
    result = normalize_period_indicator(result)
    result = normalize_team_name(result)
    result = normalize_over_under(result)
    result = normalize_moneyline(result)
    result = normalize_spread(result)
    result = normalize_whitespace(result)
    
    return result


def normalize_for_comparison(pick_text: str) -> str:
    """
    Normalizes pick text specifically for comparison purposes.
    
    This is more aggressive than normalize_pick() and is used
    when comparing expected vs actual picks in benchmarks.
    """
    if not pick_text:
        return ""
    
    # Apply standard normalization
    result = normalize_pick(pick_text)
    
    # Lowercase for comparison
    result = result.lower()
    
    # Remove all punctuation except + - .
    result = re.sub(r'[^\w\s+\-.]', '', result)
    
    # Collapse whitespace
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def extract_numeric_value(pick_text: str) -> Optional[float]:
    """
    Extracts the primary numeric value from a pick.
    
    Examples:
        "Lakers -5.5" -> -5.5
        "Over 215.5" -> 215.5
        "Lakers ML" -> None
    """
    if not pick_text:
        return None
    
    # Match spread/total numbers
    match = re.search(r'([+-]?\d+\.?\d*)', pick_text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    
    return None


def picks_match(pick1: str, pick2: str, threshold: float = 0.85) -> bool:
    """
    Determines if two picks match after normalization.
    
    Uses normalized comparison for better matching across
    different formatting styles.
    """
    from difflib import SequenceMatcher
    
    norm1 = normalize_for_comparison(pick1)
    norm2 = normalize_for_comparison(pick2)
    
    # Exact match after normalization
    if norm1 == norm2:
        return True
    
    # Fuzzy match
    ratio = SequenceMatcher(None, norm1, norm2).ratio()
    if ratio >= threshold:
        return True
    
    # Check if numeric values match (for spread/total picks)
    num1 = extract_numeric_value(norm1)
    num2 = extract_numeric_value(norm2)
    
    if num1 is not None and num2 is not None:
        # Same number, check if main terms overlap
        if abs(num1 - num2) < 0.1:
            # Remove the number and compare remaining text
            text1 = re.sub(r'[+-]?\d+\.?\d*', '', norm1).strip()
            text2 = re.sub(r'[+-]?\d+\.?\d*', '', norm2).strip()
            
            if text1 and text2:
                text_ratio = SequenceMatcher(None, text1, text2).ratio()
                if text_ratio >= 0.7:
                    return True
    
    return False
