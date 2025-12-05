import re
import logging
from typing import Optional, List
from models import ParsedPick, RawPick

logger = logging.getLogger(__name__)

RE_UNIT = re.compile(r'(\d+(\.\d+)?)\s*u(nit)?s?', re.IGNORECASE)
RE_ODDS = re.compile(r'\(([-+]?\d{3,})\)|([-+]?\d{3,})')

PATTERNS = [
    {
        'type': 'Total',
        're': re.compile(r"^(?P<dir>o|u|over|under)\s*(?P<line>\d+(\.\d+)?)\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{dir} {line}"
    },
    {
        'type': 'Moneyline',
        # FIX: Added (?:ML|Moneyline) to match both formats
        're': re.compile(r"^(?P<team>.+?)\s+(?:ML|Moneyline)\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{team} ML"
    },
    {
        'type': 'Spread',
        're': re.compile(r"^(?!over|under|o\s|u\s)(?P<team>.{2,}?)\s+(?P<spread>[-+]\d+(\.\d+)?|Pk|Pick'em|Ev)\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{team} {spread}"
    }
]

def _extract_unit(text: str) -> float:
    if not text: return 1.0
    m = RE_UNIT.search(text)
    if m:
        try:
            return float(m.group(1))
        except:
            return 1.0
    lower = text.lower()
    if 'max' in lower or 'whale' in lower: return 5.0
    return 1.0

def _extract_odds(text: str) -> Optional[int]:
    if not text: return -110
    m = RE_ODDS.search(text)
    if m:
        try:
            val = int(m.group(1) or m.group(2))
            if abs(val) > 100: return val
        except:
            pass
    return -110

def _stitch_lines(lines: List[str]) -> List[str]:
    stitched = []
    skip_next = False
    start_info_re = re.compile(r'^([-+]\d|ML|Over|Under|o\d|u\d)', re.I)
    
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
    
    if len(stitched) < len(lines):
        logger.debug(f"Stitched lines: {len(lines)} -> {len(stitched)}")
    return stitched

def parse_with_regex(raw: RawPick) -> Optional[ParsedPick]:
    lines = [l.strip() for l in raw.raw_text.split('\n') if l.strip()]
    lines = [l for l in lines if len(l) < 100 and not l.lower().startswith('http')]
    
    lines = _stitch_lines(lines)
    
    if len(lines) > 3: 
        logger.debug(f"Pick {raw.id}: Too many lines for regex ({len(lines)}). Skipping.")
        return None

    for line in lines:
        for pat in PATTERNS:
            match = pat['re'].match(line)
            if match:
                logger.debug(f"Pick {raw.id}: Matched REGEX pattern {pat['type']}")
                data = match.groupdict()
                odds_part = data.get('odds_part', '')
                
                if pat['type'] == 'Total':
                    direction = data['dir'].lower()
                    if direction.startswith('o'): data['dir'] = 'Over'
                    elif direction.startswith('u'): data['dir'] = 'Under'
                
                if pat['type'] == 'Spread':
                    spr = data['spread'].lower()
                    if spr in ['pk', "pick'em", 'ev']: data['spread'] = '-0'

                pick_val = pat['val_fmt'].format(**data)
                
                try:
                    return ParsedPick(
                        raw_pick_id=raw.id or 0,
                        league="Unknown",
                        bet_type=pat['type'],
                        pick_value=pick_val,
                        unit=_extract_unit(odds_part),
                        odds_american=_extract_odds(odds_part)
                    )
                except Exception:
                    continue
    return None