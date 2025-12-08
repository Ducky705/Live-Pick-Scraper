import re
import logging
from typing import Optional, List
from models import ParsedPick, RawPick

logger = logging.getLogger(__name__)

# Stricter Unit Regex: Must be explicitly labeled 'u', 'unit', 'star', etc.
# This allows "150u" or "1000 units" but ignores "-150" (odds).
RE_UNIT = re.compile(r'\b(?P<val>\d+(\.\d+)?)\s*(u|unit|star)s?\b', re.IGNORECASE)
RE_ODDS = re.compile(r'\(([-+]?\d{3,})\)|\b([-+]?\d{3,})\b')

PATTERNS = [
    {
        'type': 'Total',
        're': re.compile(r"^(?P<dir>o|u|over|under)\s*(?P<line>\d+(\.\d+)?)\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{dir} {line}"
    },
    {
        'type': 'Moneyline',
        're': re.compile(r"^(?P<team>.+?)\s+(?:ML|Moneyline)\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{team} ML"
    },
    {
        'type': 'Spread',
        # Stricter spread: Look for team followed by -X or +X. 
        # Excludes lines starting with O/U to avoid totals being caught as spreads.
        're': re.compile(r"^(?!over|under|o\s|u\s)(?P<team>.{2,}?)\s+(?P<spread>[-+]\d+(\.\d+)?|Pk|Pick'em|Ev)\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{team} {spread}"
    }
]

def _extract_unit(text: str) -> Optional[float]:
    if not text: return None
    
    # 1. Explicit units (e.g., "150u", "500 units", "5*")
    m = RE_UNIT.search(text)
    if m:
        try:
            return float(m.group('val'))
        except:
            pass
            
    # 2. Keywords
    lower = text.lower()
    if 'max' in lower or 'whale' in lower: return 5.0
    
    return None

def _extract_odds(text: str) -> Optional[int]:
    if not text: return None
    # Find numbers > 100 or < -100
    matches = RE_ODDS.findall(text)
    for m in matches:
        val_str = m[0] or m[1]
        try:
            val = int(val_str)
            if abs(val) >= 100: return val
        except:
            continue
    return None

def _stitch_lines(lines: List[str]) -> List[str]:
    stitched = []
    skip_next = False
    # Look for lines starting with spread/total indicators
    start_info_re = re.compile(r'^([-+]\d|ML|Over|Under|o\d|u\d)', re.I)
    
    for i in range(len(lines)):
        if skip_next:
            skip_next = False
            continue
        current = lines[i]
        if i < len(lines) - 1:
            next_line = lines[i+1]
            # If current line is just text and next line starts with numbers/bet info
            if not start_info_re.match(current) and start_info_re.match(next_line):
                stitched.append(f"{current} {next_line}")
                skip_next = True
                continue
        stitched.append(current)
    return stitched

def parse_with_regex(raw: RawPick) -> Optional[ParsedPick]:
    # Clean raw text
    lines = [l.strip() for l in raw.raw_text.split('\n') if l.strip()]
    lines = [l for l in lines if len(l) < 100 and not l.lower().startswith('http')]
    
    lines = _stitch_lines(lines)
    
    # Only try regex on short messages. Complex ones go to AI.
    if len(lines) > 4: 
        return None

    for line in lines:
        for pat in PATTERNS:
            match = pat['re'].match(line)
            if match:
                data = match.groupdict()
                odds_part = data.get('odds_part', '')
                
                if pat['type'] == 'Total':
                    direction = data['dir'].lower()
                    if direction.startswith('o'): data['dir'] = 'Over'
                    elif direction.startswith('u'): data['dir'] = 'Under'
                
                if pat['type'] == 'Spread':
                    spr = data['spread'].lower()
                    if spr in ['pk', "pick'em", 'ev']: data['spread'] = '-0'
                    # Safety: If spread is > 50 (likely a total), ignore
                    try:
                        if abs(float(data['spread'])) > 50: continue
                    except: pass

                pick_val = pat['val_fmt'].format(**data)
                
                return ParsedPick(
                    raw_pick_id=raw.id or 0,
                    league="Unknown",
                    bet_type=pat['type'],
                    pick_value=pick_val,
                    unit=_extract_unit(odds_part),
                    odds_american=_extract_odds(odds_part)
                )
    return None
