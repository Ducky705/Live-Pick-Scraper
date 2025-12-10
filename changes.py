import os

# ==============================================================================
# FIXED SIMPLE PARSER (Distinguishes Spreads vs. Odds by Magnitude)
# ==============================================================================
SIMPLE_PARSER_CONTENT = """import re
import logging
from typing import Optional, List
from models import ParsedPick, RawPick

logger = logging.getLogger(__name__)

# 1. Units: "5u", "5.5 units", "10 star"
RE_UNIT = re.compile(r'\\b(?P<val>\\d+(\\.\\d+)?)\\s*(u|unit|star)s?\\b', re.IGNORECASE)

# 2. Odds Extraction
# Looks for 3+ digit numbers with optional +/- (e.g., -110, +200, 110)
RE_ODDS = re.compile(r'(?<!\\d)([-+]?\\d{3,})(?!\\d)')

PATTERNS = [
    # 1. TOTALS (Start with O/U): "Over 215.5", "o 55.5"
    {
        'type': 'Total',
        're': re.compile(r"^(?P<dir>o|u|over|under)\\s*(?P<line>\\d+(\\.\\d+)?)\\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{dir} {line}"
    },
    # 2. PLAYER PROPS / TEAM TOTALS (Name + O/U + Line): "Jalen Hurts Over 31.5"
    {
        'type': 'Player Prop', 
        're': re.compile(r"^(?P<name>.+?)\\s+(?P<dir>over|under|o|u)\\s*(?P<line>\\d+(\\.\\d+)?)\\s*(?P<stat>[a-zA-Z\\s]+)?(?P<odds_part>.*)$", re.I),
        'val_fmt': "{name} {dir} {line} {stat}"
    },
    # 3. MONEYLINE (Explicit): "Lakers ML", "Celtics Moneyline"
    {
        'type': 'Moneyline',
        're': re.compile(r"^(?P<team>.+?)\\s+(?:ML|Moneyline|M/L)\\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{team} ML"
    },
    # 4. SPREADS / HANDICAPS (The tricky one)
    # Matches "Team -5", "Team +3.5", "Team -110" (Ambiguous)
    {
        'type': 'Spread',
        're': re.compile(r"^(?!over|under|o\\s|u\\s)(?P<team>.{2,}?)\\s+(?P<spread>[-+]\\d+(\\.\\d+)?|Pk|Pick'em|Ev)\\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{team} {spread}"
    }
]

def _extract_unit(text: str) -> Optional[float]:
    if not text: return None
    m = RE_UNIT.search(text)
    if m:
        try: return float(m.group('val'))
        except: pass
    
    lower = text.lower()
    if 'max' in lower or 'whale' in lower: return 5.0
    if 'pod' in lower or 'potd' in lower: return 3.0
    return None

def _extract_odds(text: str) -> Optional[int]:
    if not text: return None
    # Look for odds in the remaining text
    matches = RE_ODDS.findall(text)
    for m in matches:
        try:
            val = int(m)
            # Standard US odds are usually >100 or <-100
            if abs(val) >= 100: return val
        except: continue
    return None

def _stitch_lines(lines: List[str]) -> List[str]:
    stitched = []
    skip_next = False
    start_info_re = re.compile(r'^([-+]\\d|ML|Over|Under|o\\s*\\d|u\\s*\\d|[-+]\\d{3})', re.I)
    
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

def parse_with_regex(raw: RawPick) -> Optional[ParsedPick]:
    lines = [l.strip() for l in raw.raw_text.split('\\n') if l.strip()]
    lines = [l for l in lines if len(l) < 150 and not l.lower().startswith('http')]
    lines = _stitch_lines(lines)
    
    if len(lines) > 6: return None

    for line in lines:
        for pat in PATTERNS:
            match = pat['re'].match(line)
            if match:
                data = match.groupdict()
                odds_part = data.get('odds_part', '')
                
                # --- LOGIC TO HANDLE SPREAD VS ODDS ---
                if pat['type'] == 'Spread':
                    raw_spread = data['spread']
                    
                    # Handle "Pk", "Ev"
                    if raw_spread.lower() in ['pk', "pick'em", 'ev']:
                        final_spread = '-0'
                    else:
                        try:
                            val = float(raw_spread)
                            # CRITICAL CHECK: Is this a spread (-5) or Moneyline odds (-110)?
                            if abs(val) >= 100:
                                # It's actually Moneyline Odds!
                                # Example: "Lakers -150" -> Team: Lakers, Odds: -150
                                return ParsedPick(
                                    raw_pick_id=raw.id or 0,
                                    league="Unknown",
                                    bet_type="Moneyline",
                                    pick_value=f"{data['team'].strip()} ML",
                                    unit=_extract_unit(odds_part),
                                    odds_american=int(val)
                                )
                            final_spread = raw_spread
                        except:
                            continue # Not a valid number

                    # If we are here, it's a valid small number spread (e.g. -5)
                    # Now look for odds in the 'odds_part' (e.g. "+110" in "Lakers -5 +110")
                    found_odds = _extract_odds(odds_part)
                    
                    return ParsedPick(
                        raw_pick_id=raw.id or 0,
                        league="Unknown",
                        bet_type="Spread",
                        pick_value=f"{data['team'].strip()} {final_spread}",
                        unit=_extract_unit(odds_part),
                        odds_american=found_odds
                    )

                # --- HANDLING TOTALS & PROPS ---
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
                
                return ParsedPick(
                    raw_pick_id=raw.id or 0,
                    league="Unknown",
                    bet_type=pat['type'],
                    pick_value=pick_val,
                    unit=_extract_unit(odds_part),
                    odds_american=_extract_odds(odds_part)
                )
    return None
"""

def write_file(filename, content):
    print(f"Writing {filename}...")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Updated {filename}")

if __name__ == "__main__":
    write_file('simple_parser.py', SIMPLE_PARSER_CONTENT)
    print("\n🎉 Logic Fixed: Parser now correctly distinguishes Spreads (-5) from Odds (-110)!")