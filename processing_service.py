# File: ./processing_service.py
import logging
from thefuzz import process as fuzz_process

# --- Local Imports ---
from config import LEAGUE_STANDARDS, BET_TYPE_STANDARDS, PICK_STATUS_PROCESSED
from database import get_pending_raw_picks, get_or_create_capper, insert_structured_picks, update_raw_picks_status, increment_raw_pick_attempts
from ai_parser import parse_with_ai
from standardizer import get_standardized_value, clean_unit_value
from simple_parser import parse_with_regex # --- IMPROVEMENT: Import the simple parser

def process_and_standardize_pick(parsed_pick: dict, original_raw_pick: dict) -> dict | None:
    """
    Takes a parsed pick (from AI or regex) and the original raw pick,
    then standardizes and prepares it for database insertion.
    Returns a dictionary for insertion or None on failure.
    """
    final_capper_name = original_raw_pick.get('capper_name')
    if not final_capper_name:
        logging.warning(f"No capper name found in source data for raw_pick_id {original_raw_pick['id']}. Skipping.")
        return None
        
    capper_id = get_or_create_capper(final_capper_name, fuzz_process)
    if not capper_id:
        logging.warning(f"Could not get or create capper ID for '{final_capper_name}'. Skipping pick.")
        return None
    
    # Standardize league, bet_type, and unit
    standard_league = get_standardized_value(parsed_pick.get('league', 'Other'), LEAGUE_STANDARDS, 'Other')
    standard_bet_type = get_standardized_value(parsed_pick.get('bet_type', 'Unknown'), BET_TYPE_STANDARDS, 'Unknown')
    clean_unit = clean_unit_value(parsed_pick.get('unit'))

    return {
        'capper_id': capper_id, 
        'pick_date': original_raw_pick['pick_date'], 
        'league': standard_league, 
        'pick_value': parsed_pick.get('pick_value'), 
        'bet_type': standard_bet_type, 
        'unit': clean_unit, 
        'odds_american': parsed_pick.get('odds_american'),
        'source_url': original_raw_pick.get('source_url'),
        'source_unique_id': original_raw_pick.get('source_unique_id'),
    }

def run_processor():
    """
    Orchestrates the processing of raw picks using a HYBRID approach:
    1. Try a fast, simple regex parser for common formats.
    2. If that fails, fall back to the more powerful AI parser.
    """
    logging.info("Starting processing service run...")
    
    raw_picks = get_pending_raw_picks(limit=10) # Increased limit slightly
    if not raw_picks:
        logging.info("No pending raw picks to process.")
        return

    picks_to_insert = []
    processed_ids = set()
    raw_picks_for_ai = []

    # --- IMPROVEMENT: Stage 1 - Simple Regex Parser ---
    for pick in raw_picks:
        simple_parsed_pick = parse_with_regex(pick)
        if simple_parsed_pick:
            final_pick = process_and_standardize_pick(simple_parsed_pick, pick)
            if final_pick:
                picks_to_insert.append(final_pick)
                processed_ids.add(pick['id'])
        else:
            # If simple parser fails, add it to the batch for the AI
            raw_picks_for_ai.append({"raw_pick_id": pick['id'], "text": pick['raw_text']})
    
    # --- IMPROVEMENT: Stage 2 - AI Parser Fallback ---
    if raw_picks_for_ai:
        ai_parsed_picks = parse_with_ai(raw_picks_for_ai)
        
        if not ai_parsed_picks:
            logging.error("AI parsing returned no data or failed. Incrementing attempt counter for AI-bound picks.")
            failed_ids = [p['raw_pick_id'] for p in raw_picks_for_ai]
            increment_raw_pick_attempts(failed_ids)
        else:
            for parsed_pick in ai_parsed_picks:
                raw_pick_id = parsed_pick.get('raw_pick_id')
                original_pick = next((p for p in raw_picks if p['id'] == raw_pick_id), None)
                if not original_pick: continue

                final_pick = process_and_standardize_pick(parsed_pick, original_pick)
                if final_pick:
                    picks_to_insert.append(final_pick)
                    processed_ids.add(raw_pick_id)
        
    # --- Database Operations ---
    if picks_to_insert:
        insert_structured_picks(picks_to_insert)

    if processed_ids:
        update_raw_picks_status(list(processed_ids), PICK_STATUS_PROCESSED)

    logging.info("Processing service run finished.")

if __name__ == "__main__":
    run_processor()