import re
import logging
from typing import Optional, List
from models import ParsedPick, RawPick
import standardizer

logger = logging.getLogger(__name__)

# 1. Units
RE_UNIT = re.compile(r'\b(?P<val>\d+(\.\d+)?)\s*(u|unit|star)s?\b|\((?P<val_paren>\d+(\.\d+)?)(u|unit)?\)\s*$', re.IGNORECASE)

# 2. Odds
RE_ODDS = re.compile(r'(?<!\d)([-+]?\d{3,})(?!\d)')

# 3. League Headers
RE_LEAGUE_HEADER = re.compile(r'^\(?(NFL|NBA|NHL|MLB|NCAAF|NCAAB|UFC|EPL)\)?:?$', re.IGNORECASE)

# 4. Hype Terms
HYPE_TERMS = [
    "LOCK OF THE CENTURY", "WHALE PLAY", "MAX BET", "HAMMER", "BOMB", "NUKE",
    "INSIDER INFO", "FIXED", "GUARANTEED", "FREE PICK", "SYSTEM PLAY",
    "VIP", "POD", "POTD", "🔥", "💰", "🔒", "🚨", "✅"
]

PATTERNS = [
    {
        'type': 'Total',
        're': re.compile(r"^(?P<dir>o|u|over|under)\s*(?P<line>\d+(\.\d+)?)\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{dir} {line}"
    },
    {
        'type': 'Player Prop', 
        're': re.compile(r"^(?P<name>.+?)\s+(?P<dir>over|under|o|u)\s*(?P<line>\d+(\.\d+)?)\s*(?P<stat>[a-zA-Z\s]+)?(?P<odds_part>.*)$", re.I),
        'val_fmt': "{name} {dir} {line} {stat}"
    },
    {
        'type': 'Moneyline',
        're': re.compile(r"^(?P<team>.+?)\s+(?:ML|Moneyline|M/L)\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{team} ML"
    },
    {
        'type': 'Spread',
        're': re.compile(r"^(?!over|under|o\s|u\s)(?P<team>.{2,}?)\s+(?P<spread>[-+]\d+(\.\d+)?|Pk|Pick'em|Ev)\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{team} {spread}"
    }
]

def _clean_hype_text(text: str) -> str:
    text = text.upper()
    for term in HYPE_TERMS:
        text = text.replace(term, "")
    text = re.sub(r'[!*]', '', text)
    return text.strip()

def _extract_unit(text: str) -> Optional[float]:
    if not text: return None
    m = RE_UNIT.search(text)
    if m:
        val = m.group('val') or m.group('val_paren')
        try: return float(val)
        except: pass
    lower = text.lower()
    if 'max' in lower or 'whale' in lower: return 5.0
    if 'pod' in lower or 'potd' in lower: return 3.0
    return None

def _extract_odds(text: str) -> Optional[int]:
    if not text: return None
    matches = RE_ODDS.findall(text)
    for m in matches:
        try:
            val = int(m)
            if abs(val) >= 100: return val
        except: continue
    return None

def _stitch_lines(lines: List[str]) -> List[str]:
    stitched = []
    skip_next = False
    start_info_re = re.compile(r'^([-+]\d|ML|Over|Under|o\s*\d|u\s*\d|[-+]\d{3})', re.I)
    
    for i in range(len(lines)):
        if skip_next:
            skip_next = False
            continue
        current = lines[i]
        if i < len(lines) - 1:
            next_line = lines[i+1]
            if not start_info_re.match(current) and start_info_re.match(next_line):
                stitched.append(f"{current} {next_line}")
                skip_next = True
                continue
        stitched.append(current)
    return stitched

def parse_with_regex(raw: RawPick) -> List[ParsedPick]:
    if not raw.raw_text: return []
    clean_text = raw.raw_text
    lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
    lines = [l for l in lines if len(l) < 150 and not l.lower().startswith('http')]
    lines = _stitch_lines(lines)
    
    results = []
    current_league = "Unknown"

    for line in lines:
        header_match = RE_LEAGUE_HEADER.match(line)
        if header_match:
            raw_league = header_match.group(1) or line.replace("(", "").replace(")", "").replace(":", "")
            current_league = standardizer.standardize_league(raw_league)
            continue

        clean_line = _clean_hype_text(line)
        
        for pat in PATTERNS:
            match = pat['re'].match(clean_line)
            if match:
                data = match.groupdict()
                odds_part = data.get('odds_part', '')
                
                if pat['type'] == 'Spread':
                    raw_spread = data['spread']
                    if raw_spread.lower() in ['pk', "pick'em", 'ev']:
                        final_spread = '-0'
                    else:
                        try:
                            val = float(raw_spread)
                            if abs(val) >= 100:
                                results.append(ParsedPick(
                                    raw_pick_id=raw.id or 0,
                                    league=current_league,
                                    bet_type="Moneyline",
                                    pick_value=f"{data['team'].strip()} ML",
                                    unit=_extract_unit(line),
                                    odds_american=int(val)
                                ))
                                break
                            final_spread = raw_spread
                        except: continue

                    results.append(ParsedPick(
                        raw_pick_id=raw.id or 0,
                        league=current_league,
                        bet_type="Spread",
                        pick_value=f"{data['team'].strip()} {final_spread}",
                        unit=_extract_unit(line),
                        odds_american=_extract_odds(line)
                    ))
                    break

                if pat['type'] == 'Total':
                    direction = data['dir'].lower()
                    if direction.startswith('o'): data['dir'] = 'Over'
                    elif direction.startswith('u'): data['dir'] = 'Under'
                
                if pat['type'] == 'Player Prop':
                    direction = data['dir'].lower()
                    if direction.startswith('o'): data['dir'] = 'Over'
                    elif direction.startswith('u'): data['dir'] = 'Under'
                    if not data.get('stat'): data['stat'] = ''

                pick_val = pat['val_fmt'].format(**data).strip()
                
                results.append(ParsedPick(
                    raw_pick_id=raw.id or 0,
                    league=current_league,
                    bet_type=pat['type'],
                    pick_value=pick_val,
                    unit=_extract_unit(line),
                    odds_american=_extract_odds(line)
                ))
                break
        
    return results
