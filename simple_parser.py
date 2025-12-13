import re
import logging
from typing import Optional, List
from models import ParsedPick, RawPick
import standardizer

logger = logging.getLogger(__name__)

# 1. Units
RE_UNIT = re.compile(r'\b(?P<val>\d+(\.\d+)?)\s*(u|unit|star)s?\b|\((?P<val_paren>\d+(\.\d+)?)(u|unit)?\)\s*$', re.IGNORECASE)
RE_ODDS = re.compile(r'(?<!\d)([-+]?\d{3,})(?!\d)')

# 2. Hype Terms
HYPE_TERMS = [
    "LOCK OF THE CENTURY", "WHALE PLAY", "MAX BET", "HAMMER", "BOMB", "NUKE",
    "INSIDER INFO", "FIXED", "GUARANTEED", "FREE PICK", "SYSTEM PLAY",
    "VIP", "POD", "POTD", "🔥", "💰", "🔒", "🚨", "✅", "©", "®", "|", "[", "]", ")",
    "analysis", "reasoning", "writeup", "prediction", "dm", "in bio", "year", "season"
]

PATTERNS = [
    {
        'type': 'Total',
        're': re.compile(r"(^|\s)(?P<dir>(over|under|o|u))\s*(?P<line>\d+(\.\d+)?)\s*(?P<odds_part>[-+]\d+)?", re.I),
        'val_fmt': "{dir} {line}"
    },
    {
        'type': 'Spread',
        're': re.compile(r"(?P<team>[a-zA-Z0-9\s'.&]{2,30}?)\s+(?P<spread>[-+]\d+(\.\d+)?|Pk|Pick'em|Ev)\b(?!.*(?:over|under))", re.I),
        'val_fmt': "{team} {spread}"
    },
    {
        'type': 'Moneyline',
        're': re.compile(r"(?P<team>[a-zA-Z0-9\s'.&]{2,30}?)\s+(?:ML|Moneyline|M\/L)", re.I),
        'val_fmt': "{team} ML"
    }
]

def _clean_text(text: str) -> str:
    text = re.sub(r'\[OCR RESULT.*?\]:?', '', text, flags=re.I)
    
    # NEW: Aggressive Unit/SU Stripping
    # 1. Strip "(5u)", "5u ", "5 u "
    text = re.sub(r'^\s*\(?\d+(\.\d+)?\s*u\)?\s+', '', text, flags=re.I)
    # 2. Strip "(SU)", "SU " (Straight Up/Unit)
    text = re.sub(r'^\s*\(?su\)?\s+', '', text, flags=re.I)
    
    for term in HYPE_TERMS:
        text = re.sub(re.escape(term), "", text, flags=re.IGNORECASE)
    text = re.sub(r'[!*@#=]', '', text)
    text = text.lstrip('.,- ') 
    return text.strip()

def parse_with_regex(raw: RawPick) -> List[ParsedPick]:
    if not raw.raw_text: return []
    
    lines = raw.raw_text.split('\n')
    cleaned_lines = [_clean_text(l) for l in lines if len(l.strip()) > 3]
    
    temp_results = []
    
    for line in cleaned_lines:
        if re.search(r'^\d+:\d+', line) or re.search(r'^\d+/\d+', line):
            continue

        for pat in PATTERNS:
            match = pat['re'].search(line)
            if match:
                data = match.groupdict()
                
                if pat['type'] in ['Spread', 'Moneyline']:
                    team_name = data.get('team', '').strip()
                    lower_name = team_name.lower()
                    
                    if len(team_name) < 2: continue
                    if team_name[0].isdigit() and team_name not in {'49ers', '76ers', '1st half', '2nd half'}: continue
                    
                    if lower_name in {'bet', 'pick', 'game', 'today', 'profit', 'ticket', 'wager'}: continue
                    if "unit bet" in lower_name or "unit play" in lower_name: continue
                    if lower_name in {'points', 'assists', 'rebounds', 'sog', 'shots', 'goals', 'saves', 'strikeouts', 'hits', 'runs'}: continue

                if pat['type'] == 'Total':
                    direction = data['dir'].lower()
                    if direction.startswith('o'): data['dir'] = 'Over'
                    elif direction.startswith('u'): data['dir'] = 'Under'
                
                if pat['type'] == 'Spread':
                    if data['spread'].lower() in ['pk', "pick'em", 'ev']:
                        data['spread'] = '+0'
                    data['spread'] = data['spread'].replace(' ', '')

                pick_val = pat['val_fmt'].format(**data).strip()
                
                odds = None
                odds_match = RE_ODDS.search(line)
                if odds_match:
                    try: 
                        val = int(odds_match.group(1))
                        if abs(val) >= 100 and abs(val) < 10000: odds = val
                    except: pass

                units = None
                unit_match = RE_UNIT.search(line)
                if unit_match:
                    try:
                        u_str = unit_match.group('val') or unit_match.group('val_paren')
                        units = float(u_str)
                    except: pass

                league = standardizer.infer_league(pick_val)

                temp_results.append(ParsedPick(
                    raw_pick_id=raw.id or 0,
                    league=league,
                    bet_type=pat['type'],
                    pick_value=pick_val,
                    unit=units,
                    odds_american=odds
                ))
                break

    unique_picks = []
    seen = set()
    for p in temp_results:
        key = (p.pick_value, p.bet_type)
        if key not in seen:
            seen.add(key)
            unique_picks.append(p)

    return unique_picks
