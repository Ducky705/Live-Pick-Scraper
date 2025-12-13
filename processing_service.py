import logging
import time
import re
from difflib import SequenceMatcher
from typing import List, Set, Tuple
from thefuzz import process as fuzz_process

from database import db
from models import StandardizedPick, ParsedPick, RawPick
import simple_parser
import ai_parser
import standardizer

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
MIN_TEAM_MATCH_SCORE = 85 # Fuzzy match confidence required to accept a Regex team
AI_FALLBACK_THRESHOLD = 0.4 # If garbage ratio is high, don't even try AI

# 1. GLOBAL IGNORE
GLOBAL_IGNORE_TERMS = [
    "account balance", "pending bets", "current balance", "available balance",
    "bet slip", "wager:", "to win:", "risk:", "payout:", 
    "parlay (", "parlay:", "same game parlay", "sgp", "teaser", "+ leg"
]

# 2. LINE IGNORE
UI_NOISE_TERMS = [
    "deposit", "cash out", "bets placed", "my bets", "share my bet", "book a bet",
    "login", "sign up", "forgot password", "face id", "touch id",
    "combines 3 passes", "ocr result", "making money as usual",
    "see less", "bankroll", "unit =", "units =", "ecapper", "capper:",
    "betslip", "straight"
]

# Build a flattened set of valid teams for quick lookup
VALID_TEAMS_LIST = []
for league, teams in standardizer.LEAGUE_KEYWORDS.items():
    for team in teams:
        VALID_TEAMS_LIST.append(team)

def clean_ocr_garbage(text: str) -> str:
    if not text: return ""
    lower_full = text.lower()
    if any(term in lower_full for term in GLOBAL_IGNORE_TERMS):
        return ""
    text = re.sub(r'\[OCR RESULT.*?\]:?', '', text, flags=re.I)
    
    lines = text.split('\n')
    valid_lines = []
    seen_lines = set() 
    prev_line = ""
    bet_pattern = re.compile(r'[-+]\d+|o\s*\d|u\s*\d|over|under', re.I)

    for line in lines:
        stripped = line.strip()
        lower_line = stripped.lower()
        if len(stripped) < 3: continue 
        if any(term in lower_line for term in UI_NOISE_TERMS): continue

        if prev_line:
            similarity = SequenceMatcher(None, prev_line, stripped).ratio()
            if similarity > 0.85: continue
        
        letters = sum(c.isalpha() for c in stripped)
        total = len(stripped)
        ratio = letters / total if total > 0 else 0
        
        # Keep garbage lines ONLY if they look like a bet
        if ratio < 0.4:
            if not bet_pattern.search(stripped): continue
            
        clean_key = re.sub(r'\s+', '', lower_line)
        if clean_key in seen_lines: continue

        seen_lines.add(clean_key)
        valid_lines.append(stripped)
        prev_line = stripped
        
    return "\n".join(valid_lines)

def validate_team_fuzzy(team_name: str) -> bool:
    """Returns True if team_name fuzzily matches a known team."""
    # 1. Direct Check
    if len(team_name) < 2: return False
    
    # 2. Heuristics for non-standard lists (Colleges)
    if "state" in team_name.lower() or "univ" in team_name.lower(): return True
    
    # 3. Fuzzy Check
    best_match, score = fuzz_process.extractOne(team_name, VALID_TEAMS_LIST)
    return score >= MIN_TEAM_MATCH_SCORE

def get_existing_pick_signatures(capper_ids: List[int], dates: List[str]) -> Set[Tuple[int, str, str, str]]:
    if not db.client or not capper_ids: return set()
    try:
        date_strs = [d.isoformat() if hasattr(d, 'isoformat') else str(d) for d in dates]
        response = db.client.table('live_structured_picks') \
            .select('capper_id, pick_date, pick_value, bet_type') \
            .in_('capper_id', capper_ids) \
            .in_('pick_date', date_strs) \
            .execute()
        existing = set()
        for item in response.data:
            sig = (item['capper_id'], item['pick_date'], item['pick_value'], item['bet_type'])
            existing.add(sig)
        return existing
    except Exception: return set()

def process_picks():
    start_time = time.time()
    raw_picks = db.get_pending_raw_picks(limit=10)
    if not raw_picks: 
        print("💤 No pending picks found in DB.")
        return

    print(f"\n📥 PROCESSING BATCH: {len(raw_picks)} Messages")

    to_standardize = []
    ai_queue = [] # Picks that failed Regex validation
    processed_ids = []

    for pick in raw_picks:
        clean_text = clean_ocr_garbage(pick.raw_text)
        pick.raw_text = clean_text 
        
        if len(clean_text) < 3: 
            processed_ids.append(pick.id)
            continue

        # --- STEP 1: REGEX PASS ---
        simple_picks = simple_parser.parse_with_regex(pick)
        valid_simple_picks = []

        # --- STEP 2: VALIDATION PASS ---
        for sp in simple_picks:
            is_valid = True
            # Only validate Teams, Totals usually safe
            if sp.bet_type in ['Spread', 'Moneyline']:
                team_part = sp.pick_value.replace(" ML", "").split(" -")[0].split(" +")[0].strip()
                if not validate_team_fuzzy(team_part):
                    is_valid = False
            
            if is_valid:
                valid_simple_picks.append(sp)

        # --- STEP 3: DECISION GATE ---
        if valid_simple_picks:
            print(f"   ⚡ Regex found {len(valid_simple_picks)} valid picks in ID {pick.id}")
            for sp in valid_simple_picks:
                to_standardize.append((sp, pick))
            processed_ids.append(pick.id)
        else:
            # If Regex found NOTHING, or what it found was INVALID, send to AI
            print(f"   🤔 Regex unsure for ID {pick.id} (found {len(simple_picks)} candidates, 0 valid). Queueing AI...")
            ai_queue.append(pick)

    # --- STEP 4: AI RESCUE ---
    if ai_queue:
        try:
            ai_results = ai_parser.parse_with_ai(ai_queue)
            for parsed in ai_results:
                orig = next((p for p in ai_queue if p.id == parsed.raw_pick_id), None)
                if orig:
                    # AI is the final authority, assume it's right if it adheres to JSON schema
                    to_standardize.append((parsed, orig))
                    if orig.id not in processed_ids:
                        processed_ids.append(orig.id)
            
            # Mark all AI attempts as processed
            for p in ai_queue:
                if p.id not in processed_ids: processed_ids.append(p.id)
        except Exception as e:
            logger.error(f"AI batch failed: {e}")
            failed_ids = [p.id for p in ai_queue]
            db.increment_attempts(failed_ids)
            processed_ids = [pid for pid in processed_ids if pid not in failed_ids]

    # --- STEP 5: SAVE TO DB ---
    potential_picks = []
    involved_capper_ids = []
    involved_dates = []
    unknown_capper_id = None

    for parsed, raw in to_standardize:
        capper_id = db.get_or_create_capper(raw.capper_name, fuzz_process)
        if not capper_id:
            if not unknown_capper_id:
                unknown_capper_id = db.get_or_create_capper("Unknown Capper", fuzz_process)
            capper_id = unknown_capper_id

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

    if potential_picks:
        existing_sigs = get_existing_pick_signatures(list(set(involved_capper_ids)), list(set(involved_dates)))
        final_picks = []
        seen_in_batch = set()

        for p in potential_picks:
            p_date_str = p.pick_date.isoformat() if hasattr(p.pick_date, 'isoformat') else str(p.pick_date)
            sig = (p.capper_id, p_date_str, p.pick_value, p.bet_type)
            if sig in existing_sigs: continue
            if sig in seen_in_batch: continue
            final_picks.append(p)
            seen_in_batch.add(sig)

        if final_picks:
            db.insert_structured_picks(final_picks)
            print(f"✅ Inserted {len(final_picks)} unique picks into DB.")
        else:
            print("✅ All picks were duplicates.")

    if processed_ids:
        db.update_raw_status(processed_ids, 'processed')
    
    print(f"⏱️  Batch finished in {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    process_picks()
