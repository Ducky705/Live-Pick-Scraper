import logging
import json
import os
import time
import re
from typing import List
from thefuzz import process as fuzz_process

from database import db
from models import ParsedPick, StandardizedPick
import simple_parser
import ai_parser
import standardizer

logger = logging.getLogger(__name__)

OUTPUT_FILE = "extracted_picks.jsonl"

def sanitize_text(text: str) -> str:
    if not text: return ""
    # Remove non-printable control characters (except newlines/tabs)
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

def append_to_local_file(picks: List[StandardizedPick]):
    try:
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
            for p in picks:
                data = p.model_dump()
                data['pick_date'] = data['pick_date'].isoformat()
                # Sanitize string fields
                if data.get('pick_value'):
                    data['pick_value'] = sanitize_text(data['pick_value'])
                f.write(json.dumps(data) + "\n")
        print(f"✅ Saved {len(picks)} picks to {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Failed to write to local file: {e}")

def print_picks_to_console(picks: List[StandardizedPick]):
    if not picks: return
    print(f"\n🚀 EXTRACTED {len(picks)} NEW PICKS:")
    print("-" * 60)
    for p in picks:
        # Sanitize for display
        clean_pick = sanitize_text(p.pick_value)
        pick_str = (clean_pick[:45] + '..') if len(clean_pick) > 45 else clean_pick
        print(f"[{p.league:<4}] {p.bet_type:<10} | {pick_str:<48} | {p.odds_american if p.odds_american else '-':<4} | {p.unit if p.unit else '-':<4}u")
    print("-" * 60)

def filter_duplicates(picks: List[StandardizedPick]) -> List[StandardizedPick]:
    if not picks: return []
    unique_picks = []
    seen = set()
    for p in picks:
        # Sanitize before dedupe check
        clean_val = sanitize_text(p.pick_value)
        p.pick_value = clean_val
        
        sig = (p.capper_id, p.pick_date, clean_val, p.bet_type)
        if sig not in seen:
            unique_picks.append(p)
            seen.add(sig)
    return unique_picks

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
    failed_ids = []

    # 2. Parse
    for pick in raw_picks:
        if len(pick.raw_text) < 50 and "\n" not in pick.raw_text:
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
            
            for p in ai_batch:
                if p.id not in processed_ids:
                    processed_ids.append(p.id)

        except Exception as e:
            logger.error(f"AI batch failed: {e}")
            for p in ai_batch:
                processed_ids.append(p.id)

    # 4. Standardize & Save
    potential_picks = []
    
    for parsed, raw in to_standardize:
        capper_id = db.get_or_create_capper(raw.capper_name, fuzz_process)
        if not capper_id: capper_id = 9999 

        std_league = standardizer.standardize_league(parsed.league)
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

    final_picks = []
    if potential_picks:
        final_picks = filter_duplicates(potential_picks)
        if final_picks:
            # LOCAL DEBUG: NO DB INSERT
            append_to_local_file(final_picks)
            print_picks_to_console(final_picks)

    # 5. Update Status
    if processed_ids:
        db.update_raw_status(processed_ids, 'processed')
    
    # 6. Stats
    duration = time.time() - start_time
    print(f"⏱️  Batch finished in {duration:.2f}s")

if __name__ == "__main__":
    process_picks()
