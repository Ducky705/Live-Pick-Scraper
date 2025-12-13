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
    "see less", "bankroll", "unit =", "units =", "ecapper", "capper:",
    "betslip", "parlay", "teaser", "straight", "risk", "win"
]

def clean_ocr_garbage(text: str) -> str:
    if not text: return ""
    
    # Remove headers
    text = text.replace("[OCR RESULT (Combines 3 Passes)]:", "")
    
    lines = text.split('\n')
    valid_lines = []
    prev_line = ""
    
    for line in lines:
        stripped = line.strip()
        lower_line = stripped.lower()
        
        # 1. Skip very short lines
        if len(stripped) < 3: continue 
        
        # 2. Skip Sportsbook UI Noise
        if any(term in lower_line for term in UI_NOISE_TERMS):
            continue

        # 3. Fuzzy Consecutive Deduplication
        if prev_line:
            similarity = SequenceMatcher(None, prev_line, stripped).ratio()
            if similarity > 0.85:
                continue
        
        # 4. Alphanumeric Density Check
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
    
    # Increase batch size slightly for efficiency
    raw_picks = db.get_pending_raw_picks(limit=10)
    if not raw_picks: 
        print("💤 No pending picks found in DB.")
        return

    print(f"\n📥 PROCESSING BATCH: {len(raw_picks)} Messages")

    to_standardize = []
    ai_batch = []
    processed_ids = []

    for pick in raw_picks:
        # 1. Clean Text
        clean_text = clean_ocr_garbage(pick.raw_text)
        pick.raw_text = clean_text 
        
        if len(clean_text) < 5: 
            processed_ids.append(pick.id)
            continue

        # 2. Hybrid Strategy: Regex First
        simple_picks = simple_parser.parse_with_regex(pick)
        
        if simple_picks:
            print(f"   ⚡ Regex found {len(simple_picks)} picks in ID {pick.id}")
            for sp in simple_picks:
                to_standardize.append((sp, pick))
            processed_ids.append(pick.id)
        else:
            # 3. Fallback to AI
            print(f"   🤖 Regex failed for ID {pick.id}, queueing for AI...")
            ai_batch.append(pick)

    # 4. Run AI Batch
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

    # 5. Standardize & Deduplicate
    potential_picks = []
    involved_capper_ids = []
    involved_dates = []

    # Cache "Unknown Capper" ID to avoid repeated DB calls
    unknown_capper_id = None

    for parsed, raw in to_standardize:
        # Dynamic Capper Lookup
        capper_id = db.get_or_create_capper(raw.capper_name, fuzz_process)
        
        if not capper_id:
            # If still None, get/create 'Unknown Capper' dynamically
            if not unknown_capper_id:
                unknown_capper_id = db.get_or_create_capper("Unknown Capper", fuzz_process)
            capper_id = unknown_capper_id

        # League & Bet Type Standardization
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
