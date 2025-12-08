import logging
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
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

def get_existing_pick_signatures(capper_ids: List[int], dates: List[str]) -> Set[Tuple[int, str, str, str]]:
    """
    Queries the DB to find existing picks for these cappers on these dates
    to prevent inserting duplicates across different batches.
    """
    if not db.client or not capper_ids:
        return set()
    
    try:
        # Convert dates to ISO strings if they aren't already
        date_strs = [d.isoformat() if hasattr(d, 'isoformat') else str(d) for d in dates]
        
        # Fetch existing picks for these cappers on these dates
        response = db.client.table('live_structured_picks') \
            .select('capper_id, pick_date, pick_value, bet_type') \
            .in_('capper_id', capper_ids) \
            .in_('pick_date', date_strs) \
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

    print(f"\n📥 PROCESSING BATCH: {len(raw_picks)} Messages")
    for p in raw_picks:
        print(f"   - ID {p.id}: {p.capper_name} ({len(p.raw_text)} chars)")

    to_standardize = []
    ai_batch = []
    processed_ids = []

    # 2. Parse
    for pick in raw_picks:
        # Heuristic: If short and simple, try Regex first to save AI tokens
        if len(pick.raw_text) < 150 and "\n" not in pick.raw_text:
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
