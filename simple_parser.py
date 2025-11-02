# File: ./simple_parser.py
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _handle_ml(match: re.Match, line: str) -> dict:
    """Handles Moneyline patterns."""
    team_name = match.group('team').strip()
    odds_str = match.group('odds')
    return {
        'bet_type': 'Moneyline',
        'pick_value': f"{team_name} ML",
        'odds_american': int(odds_str.replace('(', '').replace(')', '')) if odds_str else None,
        'unit': _extract_unit(line)
    }

def _handle_spread(match: re.Match, line: str) -> dict:
    """Handles Spread patterns."""
    team_name = match.group('team').strip()
    spread = match.group('spread').strip()
    odds_str = match.group('odds')
    return {
        'bet_type': 'Spread',
        'pick_value': f"{team_name} {spread}",
        'odds_american': int(odds_str.replace('(', '').replace(')', '')) if odds_str else -110,
        'unit': _extract_unit(line)
    }

def _handle_total(match: re.Match, line: str) -> dict:
    """Handles Total patterns."""
    direction_char = match.group('dir').strip().upper()
    direction = 'Over' if direction_char.startswith('O') else 'Under'
    total = match.group('total').strip()
    odds_str = match.group('odds')
    
    teams_context = re.search(r'([\w\s.&]+)\s+(?:vs|@)\s+([\w\s.&]+)', line, re.IGNORECASE)
    if teams_context:
        team1, team2 = teams_context.group(1).strip(), teams_context.group(2).strip()
        pick_value = f"{team1} vs {team2} {direction} {total}"
    else:
        pick_value = f"{direction} {total}"
        
    return {
        'bet_type': 'Total',
        'pick_value': pick_value,
        'odds_american': int(odds_str.replace('(', '').replace(')', '')) if odds_str else -110,
        'unit': _extract_unit(line)
    }

def _extract_unit(text: str) -> float:
    """Helper to find a unit value (e.g., 2u, 1.5 units) in a string."""
    unit_match = re.search(r'(\d+[\.,]?\d*)\s*u(nit)?s?', text, re.IGNORECASE)
    if unit_match:
        unit_str = unit_match.group(1).replace(',', '.')
        return float(unit_str)
    return 1.0

# Corrected regex to handle optional parentheses around odds
SIMPLE_PATTERNS = [
    {
        'regex': re.compile(
            r"^(?P<team>[\w\s\.'\-&]+?)\s+ML\s*(?P<odds>\([+-]\d{3,}\)|[+-]\d{3,})?(?:\s+\d+[\.,]?\d*\s*u(?:nit)?s?)?$",
            re.IGNORECASE
        ),
        'handler': _handle_ml
    },
    {
        'regex': re.compile(
            r"^(?P<team>[\w\s\.'\-&]+?)\s+(?P<spread>[+-]\d{1,2}(?:[\.,]\d)?)\s*(?P<odds>\([+-]\d{3,}\)|[+-]\d{3,})?(?:\s+\d+[\.,]?\d*\s*u(?:nit)?s?)?$",
            re.IGNORECASE
        ),
        'handler': _handle_spread
    },
    {
        'regex': re.compile(
            r"^(?P<dir>Over|Under|O|U)\s+(?P<total>\d{2,3}(?:[\.,]\d)?)\s*(?P<odds>\([+-]\d{3,}\)|[+-]\d{3,})?(?:\s+\d+[\.,]?\d*\s*u(?:nit)?s?)?$",
            re.IGNORECASE
        ),
        'handler': _handle_total
    }
]

def parse_with_regex(raw_pick: dict) -> dict | None:
    """
    Iterates through simple regex patterns to attempt a high-confidence parse.
    If a single, unambiguous match is found, it returns a structured pick.
    Otherwise, returns None.
    """
    text = raw_pick['raw_text']
    found_picks = []
    
    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        
        # Skip lines that are clearly not simple picks or contain ambiguous elements
        if len(line) > 100 or line.lower().startswith(('parlay', 'teaser')) or '🏀' in line:
            continue

        for pattern in SIMPLE_PATTERNS:
            match = pattern['regex'].match(line)
            if match:
                structured_pick = pattern['handler'](match, line)
                found_picks.append(structured_pick)
                break
    
    if len(found_picks) == 1:
        final_pick = found_picks[0]
        final_pick['raw_pick_id'] = raw_pick['id']
        final_pick['league'] = 'Unknown' 
        logging.info(f"Successfully parsed raw_pick_id {raw_pick['id']} with simple regex parser.")
        return final_pick

    return None