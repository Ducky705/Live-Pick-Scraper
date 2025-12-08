import os

# ==============================================================================
# 1. IMPROVED PROCESSING SERVICE (Database-level Deduplication)
# ==============================================================================
PROCESSING_SERVICE_CONTENT = """import logging
import time
import re
from typing import List, Set, Tuple
from thefuzz import process as fuzz_process

from database import db
from models import StandardizedPick
import simple_parser
import ai_parser
import standardizer

logger = logging.getLogger(__name__)

def sanitize_text(text: str) -> str:
    if not text: return ""
    return re.sub(r'[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\x7f]', '', text)

def get_existing_pick_signatures(capper_ids: List[int], dates: List[str]) -> Set[Tuple[int, str, str, str]]:
    \"\"\"
    Queries the DB to find existing picks for these cappers on these dates
    to prevent inserting duplicates across different batches.
    \"\"\"
    if not db.client or not capper_ids:
        return set()
    
    try:
        # Convert dates to ISO strings if they aren't already
        date_strs = [d.isoformat() if hasattr(d, 'isoformat') else str(d) for d in dates]
        
        # Fetch existing picks for these cappers on these dates
        response = db.client.table('live_structured_picks') \\
            .select('capper_id, pick_date, pick_value, bet_type') \\
            .in_('capper_id', capper_ids) \\
            .in_('pick_date', date_strs) \\
            .execute()
            
        existing = set()
        for item in response.data:
            # Create a signature: (capper_id, date_str, pick_value, bet_type)
            sig = (
                item['capper_id'], 
                item['pick_date'], 
                item['pick_value'], 
                item['bet_type']
            )
            existing.add(sig)
        return existing
    except Exception as e:
        logger.error(f"Failed to fetch existing picks for deduplication: {e}")
        return set()

def process_picks():
    start_time = time.time()
    
    # 1. Get Pending Picks
    raw_picks = db.get_pending_raw_picks(limit=5)
    if not raw_picks: 
        print("💤 No pending picks found in DB.")
        return

    print(f"\\n📥 PROCESSING BATCH: {len(raw_picks)} Messages")
    for p in raw_picks:
        print(f"   - ID {p.id}: {p.capper_name} ({len(p.raw_text)} chars)")

    to_standardize = []
    ai_batch = []
    processed_ids = []

    # 2. Parse
    for pick in raw_picks:
        # Heuristic: If short and simple, try Regex first to save AI tokens
        if len(pick.raw_text) < 150 and "\\n" not in pick.raw_text:
            simple = simple_parser.parse_with_regex(pick)
            if simple:
                to_standardize.append((simple, pick))
                processed_ids.append(pick.id)
                continue
        ai_batch.append(pick)

    # 3. Run AI
    if ai_batch:
        try:
            ai_results = ai_parser.parse_with_ai(ai_batch)
            
            for parsed in ai_results:
                orig = next((p for p in ai_batch if p.id == parsed.raw_pick_id), None)
                if orig:
                    to_standardize.append((parsed, orig))
                    if orig.id not in processed_ids:
                        processed_ids.append(orig.id)
            
            # Mark items as processed even if no picks found (to stop infinite retries)
            for p in ai_batch:
                if p.id not in processed_ids:
                    processed_ids.append(p.id)

        except Exception as e:
            logger.error(f"AI batch failed: {e}")
            failed_ids = [p.id for p in ai_batch]
            db.increment_attempts(failed_ids)
            # Remove failed IDs from processed list so we don't mark them complete
            processed_ids = [pid for pid in processed_ids if pid not in failed_ids]

    # 4. Standardize
    potential_picks = []
    involved_capper_ids = []
    involved_dates = []

    for parsed, raw in to_standardize:
        capper_id = db.get_or_create_capper(raw.capper_name, fuzz_process)
        if not capper_id: capper_id = 9999 

        std_league = standardizer.standardize_league(parsed.league)
        if std_league == 'Other':
            std_league = standardizer.infer_league(parsed.pick_value)

        std_type = standardizer.standardize_bet_type(parsed.bet_type)
        std_val = standardizer.format_pick_value(parsed.pick_value, std_type, std_league)

        std = StandardizedPick(
            capper_id=capper_id,
            pick_date=raw.pick_date,
            league=std_league,
            pick_value=std_val,
            bet_type=std_type,
            unit=parsed.unit,
            odds_american=parsed.odds_american,
            source_url=raw.source_url,
            source_unique_id=raw.source_unique_id
        )
        potential_picks.append(std)
        involved_capper_ids.append(capper_id)
        involved_dates.append(raw.pick_date)

    # 5. Deduplicate against Database
    if potential_picks:
        # Fetch existing signatures from DB
        existing_sigs = get_existing_pick_signatures(list(set(involved_capper_ids)), list(set(involved_dates)))
        
        final_picks = []
        seen_in_batch = set()

        for p in potential_picks:
            # Create signature
            p_date_str = p.pick_date.isoformat() if hasattr(p.pick_date, 'isoformat') else str(p.pick_date)
            sig = (p.capper_id, p_date_str, p.pick_value, p.bet_type)
            
            if sig in existing_sigs:
                print(f"   ⚠️ Duplicate found in DB (Skipping): {p.pick_value}")
                continue
            
            if sig in seen_in_batch:
                continue

            final_picks.append(p)
            seen_in_batch.add(sig)

        if final_picks:
            db.insert_structured_picks(final_picks)
            print(f"✅ Inserted {len(final_picks)} unique picks into DB.")
        else:
            print("✅ All picks were duplicates. No new inserts.")

    # 6. Update Status
    if processed_ids:
        db.update_raw_status(processed_ids, 'processed')
    
    duration = time.time() - start_time
    print(f"⏱️  Batch finished in {duration:.2f}s")

if __name__ == "__main__":
    process_picks()
"""

# ==============================================================================
# 2. IMPROVED SIMPLE PARSER (Stricter Regex, but allows high units)
# ==============================================================================
SIMPLE_PARSER_CONTENT = """import re
import logging
from typing import Optional, List
from models import ParsedPick, RawPick

logger = logging.getLogger(__name__)

# Stricter Unit Regex: Must be explicitly labeled 'u', 'unit', 'star', etc.
# This allows "150u" or "1000 units" but ignores "-150" (odds).
RE_UNIT = re.compile(r'\\b(?P<val>\\d+(\\.\\d+)?)\\s*(u|unit|star)s?\\b', re.IGNORECASE)
RE_ODDS = re.compile(r'\\(([-+]?\\d{3,})\\)|\\b([-+]?\\d{3,})\\b')

PATTERNS = [
    {
        'type': 'Total',
        're': re.compile(r"^(?P<dir>o|u|over|under)\\s*(?P<line>\\d+(\\.\\d+)?)\\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{dir} {line}"
    },
    {
        'type': 'Moneyline',
        're': re.compile(r"^(?P<team>.+?)\\s+(?:ML|Moneyline)\\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{team} ML"
    },
    {
        'type': 'Spread',
        # Stricter spread: Look for team followed by -X or +X. 
        # Excludes lines starting with O/U to avoid totals being caught as spreads.
        're': re.compile(r"^(?!over|under|o\\s|u\\s)(?P<team>.{2,}?)\\s+(?P<spread>[-+]\\d+(\\.\\d+)?|Pk|Pick'em|Ev)\\s*(?P<odds_part>.*)$", re.I),
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
    start_info_re = re.compile(r'^([-+]\\d|ML|Over|Under|o\\d|u\\d)', re.I)
    
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
    lines = [l.strip() for l in raw.raw_text.split('\\n') if l.strip()]
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
"""

# ==============================================================================
# 3. IMPROVED MODELS (Removed Unit Cap)
# ==============================================================================
MODELS_CONTENT = """from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime, date
import re
import logging

logger = logging.getLogger(__name__)

class RawPick(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    source_unique_id: str
    source_url: str
    capper_name: str
    raw_text: str
    pick_date: date
    status: str = 'pending'
    process_attempts: int = 0
    created_at: Optional[datetime] = None

class ParsedPick(BaseModel):
    raw_pick_id: int
    league: str = "Unknown"
    bet_type: str
    pick_value: str
    unit: Optional[float] = None
    odds_american: Optional[int] = None

    @field_validator('unit', mode='before')
    @classmethod
    def validate_unit(cls, v):
        if v is None: return None
        if isinstance(v, (float, int)): 
            # Allow high units (e.g. 150, 500) as per user requirement
            return float(v)
            
        s = str(v).lower().strip()
        clean = re.sub(r'[^\\d.]', '', s)
        try:
            val = float(clean)
            return round(val, 2)
        except:
            return None

    @field_validator('odds_american', mode='before')
    @classmethod
    def validate_odds(cls, v):
        if v is None: return None
        try:
            val = int(v)
            # Odds range sanity check
            if val < -20000 or val > 20000: return None 
            # Odds usually aren't single digits (except maybe very weird formats, but standard US odds are >100 or <-100)
            if -100 < val < 100: return None
            return val
        except:
            return None

class StandardizedPick(BaseModel):
    capper_id: int
    pick_date: date
    league: str
    pick_value: str
    bet_type: str
    unit: Optional[float] = None
    odds_american: Optional[int] = None
    source_url: str
    source_unique_id: str
    result: str = 'pending'
"""

def write_file(filename, content):
    print(f"Writing {filename}...")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Updated {filename}")

if __name__ == "__main__":
    write_file('processing_service.py', PROCESSING_SERVICE_CONTENT)
    write_file('simple_parser.py', SIMPLE_PARSER_CONTENT)
    write_file('models.py', MODELS_CONTENT)
    print("\\n🎉 All improvements applied successfully!")