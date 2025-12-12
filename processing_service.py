import logging
import time
import re
from difflib import SequenceMatcher
from typing import List, Set, Tuple
from thefuzz import process as fuzz_process

from database import db
from models import StandardizedPick
import simple_parser
import ai_parser
import standardizer

logger = logging.getLogger(__name__)

# Terms found in betting app screenshots that are NOT picks
UI_NOISE_TERMS = [
    "deposit", "balance", "cash out", "bet slip", "total payout", 
    "potential payout", "wager", "to win", "accepted", "id:", 
    "bets placed", "my bets", "share my bet", "book a bet",
    "login", "sign up", "forgot password", "face id", "touch id",
    "combines 3 passes", "ocr result", "making money as usual",
    "see less", "bankroll", "unit =", "units =", "ecapper", "capper:"
]

def sanitize_text(text: str) -> str:
    if not text: return ""
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

def clean_ocr_garbage(text: str) -> str:
    """
    Advanced cleaning pipeline:
    1. Strip specific headers.
    2. Filter UI noise.
    3. Fuzzy Deduplication (Removes 'Baker under' vs 'Baker undér').
    4. Density check.
    """
    if not text: return ""
    
    # Remove the specific header that confuses parsers
    text = text.replace("[OCR RESULT (Combines 3 Passes)]:", "")
    
    lines = text.split('\n')
    valid_lines = []
    prev_line = ""
    
    for line in lines:
        stripped = line.strip()
        lower_line = stripped.lower()
        
        # 1. Skip very short lines
        if len(stripped) < 3: continue 
        
        # 2. Skip Sportsbook UI Noise & Watermarks
        if any(term in lower_line for term in UI_NOISE_TERMS):
            continue

        # 3. Fuzzy Consecutive Deduplication
        # If the current line is > 85% similar to the previous line, skip it.
        # This handles "Baker under 1.5" vs "Baker undér 1.5"
        if prev_line:
            similarity = SequenceMatcher(None, prev_line, stripped).ratio()
            if similarity > 0.85:
                continue
        
        # 4. Alphanumeric Density Check (Skip lines like "--- . . --")
        alpha_num = sum(c.isalnum() for c in stripped)
        total = len(stripped)
        if total > 0 and (alpha_num / total) < 0.5:
            continue
            
        valid_lines.append(stripped)
        prev_line = stripped
        
    return "\n".join(valid_lines)

def get_existing_pick_signatures(capper_ids: List[int], dates: List[str]) -> Set[Tuple[int, str, str, str]]:
    if not db.client or not capper_ids:
        return set()
    
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
    except Exception as e:
        logger.error(f"Failed to fetch existing picks: {e}")
        return set()

def process_picks():
    start_time = time.time()
    
    raw_picks = db.get_pending_raw_picks(limit=5)
    if not raw_picks: 
        print("💤 No pending picks found in DB.")
        return

    print(f"\n📥 PROCESSING BATCH: {len(raw_picks)} Messages")
    for p in raw_picks:
        print(f"   - ID {p.id}: {p.capper_name} ({len(p.raw_text)} chars)")

    to_standardize = []
    ai_batch = []
    processed_ids = []

    for pick in raw_picks:
        # CLEAN OCR NOISE HERE
        pick.raw_text = clean_ocr_garbage(pick.raw_text)
        
        # Heuristic: If short and simple, try Regex first
        if len(pick.raw_text) < 200 and "\n" not in pick.raw_text:
            simple_picks = simple_parser.parse_with_regex(pick)
            if simple_picks:
                # Regex parser now returns a LIST of picks
                for sp in simple_picks:
                    to_standardize.append((sp, pick))
                processed_ids.append(pick.id)
                continue
        
        # If regex failed or text is long/complex, send to AI
        ai_batch.append(pick)

    if ai_batch:
        try:
            ai_results = ai_parser.parse_with_ai(ai_batch)
            for parsed in ai_results:
                orig = next((p for p in ai_batch if p.id == parsed.raw_pick_id), None)
                if orig:
                    to_standardize.append((parsed, orig))
                    if orig.id not in processed_ids:
                        processed_ids.append(orig.id)
            
            for p in ai_batch:
                if p.id not in processed_ids: processed_ids.append(p.id)

        except Exception as e:
            logger.error(f"AI batch failed: {e}")
            failed_ids = [p.id for p in ai_batch]
            db.increment_attempts(failed_ids)
            processed_ids = [pid for pid in processed_ids if pid not in failed_ids]

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
