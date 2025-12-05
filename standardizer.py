import re
from typing import Optional
import config

def standardize_league(val: str) -> str:
    if not val: return 'Other'
    val = val.upper().strip()
    if val in config.LEAGUE_MAP: return config.LEAGUE_MAP[val]
    aliases = {
        'NCAA FOOTBALL': 'NCAAF', 'CFB': 'NCAAF',
        'NCAA BASKETBALL': 'NCAAB', 'CBB': 'NCAAB', 'COLLEGE BASKETBALL': 'NCAAB',
        'PREMIER LEAGUE': 'EPL', 'CHAMPIONS LEAGUE': 'UCL',
        'MMA': 'UFC', 'FIGHTING': 'UFC', 'KBO': 'MLB', 'NPB': 'MLB'
    }
    if val in aliases: return aliases[val]
    return 'Other'

def standardize_bet_type(val: str) -> str:
    if not val: return 'Unknown'
    val = val.upper().strip()
    mapping = {
        'MONEYLINE': 'Moneyline', 'ML': 'Moneyline',
        'SPREAD': 'Spread', 'POINT SPREAD': 'Spread', 'RUN LINE': 'Spread', 'PUCK LINE': 'Spread',
        'TOTAL': 'Total', 'OVER/UNDER': 'Total', 'O/U': 'Total',
        'PLAYER PROP': 'Player Prop', 'PROP': 'Player Prop',
        'TEAM PROP': 'Team Prop', 'GAME PROP': 'Game Prop',
        'PARLAY': 'Parlay', 'TEASER': 'Teaser', 'FUTURE': 'Future',
        'PERIOD': 'Period', 'QUARTER': 'Period', 'HALF': 'Period', '1H': 'Period', '1Q': 'Period'
    }
    for k, v in mapping.items():
        if k in val: return v
    return 'Unknown'

def _smart_title_case(text: str) -> str:
    if not text: return ""
    text = text.title()
    acronyms = {
        r'\bMl\b': 'ML', r'\bNfl\b': 'NFL', r'\bNba\b': 'NBA', r'\bMlb\b': 'MLB',
        r'\bNhl\b': 'NHL', r'\bNcaaf\b': 'NCAAF', r'\bNcaab\b': 'NCAAB',
        r'\bUfc\b': 'UFC', r'\bPra\b': 'PRA', r'\bSog\b': 'SOG',
        r'\b1H\b': '1H', r'\b2H\b': '2H', r'\b1Q\b': '1Q', r'\b2Q\b': '2Q',
        r'\b3Q\b': '3Q', r'\b4Q\b': '4Q', r'\bVs\b': 'vs'
    }
    for pattern, replacement in acronyms.items():
        text = re.sub(pattern, replacement, text)
    return text

def format_pick_value(pick: str, bet_type: str, league: str) -> str:
    if not pick: return "Unknown Pick"
    pick = pick.strip()
    pick = _smart_title_case(pick)
    
    if bet_type == 'Unknown': return pick

    if bet_type == 'Moneyline':
        clean = re.sub(r'\bML\b|\bMoneyline\b', '', pick, flags=re.I).strip()
        return f"{clean} ML"

    if bet_type == 'Spread':
        match = re.search(r'(.+?)\s*([-+]\d+(\.\d+)?)', pick)
        if match:
            team = match.group(1).strip()
            spread = match.group(2).strip()
            return f"{team} {spread}"
        return pick

    if bet_type == 'Total':
        pick = re.sub(r'\b(O|Over)\s*(\d)', r'Over ', pick, flags=re.I)
        pick = re.sub(r'\b(U|Under)\s*(\d)', r'Under ', pick, flags=re.I)
        return pick

    if bet_type == 'Player Prop':
        if ':' not in pick:
            parts = pick.split()
            if len(parts) > 2:
                return f"{parts[0]} {parts[1]}: {' '.join(parts[2:])}"
        return pick

    return pick
