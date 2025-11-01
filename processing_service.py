# File: ./processing_service.py
import logging
from thefuzz import process as fuzz_process

# --- Local Imports ---
from config import LEAGUE_STANDARDS, BET_TYPE_STANDARDS, PICK_STATUS_PROCESSED
from database import get_pending_raw_picks, get_or_create_capper, insert_structured_picks, update_raw_picks_status, increment_raw_pick_attempts
from ai_parser import parse_with_ai
from standardizer import get_standardized_value, clean_unit_value

def run_processor():
    """
    Orchestrates the processing of raw picks with a resilient retry mechanism.
    """
    logging.info("Starting processing service run...")
    
    raw_picks = get_pending_raw_picks(limit=5)
    if not raw_picks:
        logging.info("No pending raw picks to process.")
        return

    raw_picks_for_ai = [{"raw_pick_id": p['id'], "text": p['raw_text']} for p in raw_picks]
    parsed_picks = parse_with_ai(raw_picks_for_ai)

    if not parsed_picks:
        logging.error("AI parsing returned no data or failed. Incrementing attempt counter for these picks.")
        failed_ids = [p['id'] for p in raw_picks]
        increment_raw_pick_attempts(failed_ids)
        return
    
    picks_to_insert = []
    processed_ids = set()

    for parsed_pick in parsed_picks:
        raw_pick_id = parsed_pick.get('raw_pick_id')
        original_pick = next((p for p in raw_picks if p['id'] == raw_pick_id), None)
        if not original_pick: continue

        # --- START OF FIX #2 ---
        # The AI's job is ONLY to parse the bet. The capper name comes directly and ONLY from the scraper data.
        # This simplifies the AI's task and removes a major source of errors.
        final_capper_name = original_pick.get('capper_name')
        # --- END OF FIX #2 ---

        if not final_capper_name:
            logging.warning(f"No capper name found in source data for raw_pick_id {raw_pick_id}. Skipping.")
            continue
            
        capper_id = get_or_create_capper(final_capper_name, fuzz_process)
        if not capper_id:
            logging.warning(f"Could not get or create capper ID for '{final_capper_name}'. Skipping pick.")
            continue
        
        standard_league = get_standardized_value(parsed_pick.get('league', 'Other'), LEAGUE_STANDARDS, 'Other')
        standard_bet_type = get_standardized_value(parsed_pick.get('bet_type', 'Unknown'), BET_TYPE_STANDARDS, 'Unknown')
        clean_unit = clean_unit_value(parsed_pick.get('unit')) 

        picks_to_insert.append({
            'capper_id': capper_id, 
            'pick_date': original_pick['pick_date'], 
            'league': standard_league, 
            'pick_value': parsed_pick.get('pick_value'), 
            'bet_type': standard_bet_type, 
            'unit': clean_unit, 
            'odds_american': parsed_pick.get('odds_american'),
            'source_url': original_pick.get('source_url'),
            'source_unique_id': original_pick.get('source_unique_id'),
        })
        processed_ids.add(raw_pick_id)
        
    if picks_to_insert:
        insert_structured_picks(picks_to_insert)

    if processed_ids:
        update_raw_picks_status(list(processed_ids), PICK_STATUS_PROCESSED)

    logging.info("Processing service run finished.")

if __name__ == "__main__":
    run_processor()