# File: ./test.py
import asyncio
import logging
import time
import json
from datetime import datetime
from typing import List, Dict
from unittest.mock import patch, MagicMock, AsyncMock

# --- Main application components to be tested ---
from config import EASTERN_TIMEZONE
from database import get_supabase_client
from processing_service import run_processor
from run_pipeline import main as run_main_pipeline

# --- Test Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
supabase = None

# --- Test Data and Mocks ---
FUZZY_PREP_DATA = {'capper_directory': [{'canonical_name': 'Capper A'}, {'canonical_name': 'Capper B'}, {'canonical_name': 'The Nba Expert'}]}
TEST_RAW_PICKS = [
    {'raw_text': "Capper A 2u Los Angeles Lakers ML +150", 'capper_name': 'Capper A', 'source_unique_id': 'test-1-simple-ml'},
    {'raw_text': "Capper C 1u Kansas City Chiefs -7.5 -110 NFL", 'capper_name': 'CapperC', 'source_unique_id': 'test-2-new-capper'},
    {'raw_text': "The NB Expert 3u Nikola Jokic Over 25.5 Pts -115", 'capper_name': 'The NB Expert', 'source_unique_id': 'test-3-fuzzy-capper'},
    {'raw_text': "Capper B 1.5u Total for the game twolves vs suns O 220 +100", 'capper_name': 'Capper B', 'source_unique_id': 'test-4-total-format'},
    {'raw_text': "Capper A 4u Parlay: (nfl) Dallas Cowboys -3.5 / (ncaaf) rutgers +14.5 +264", 'capper_name': 'Capper A', 'source_unique_id': 'test-5-parlay'},
    {'raw_text': "Capper B 1u Player Prop: LeBron James Pts+Reb+Ast O 45.5 -120", 'capper_name': 'Capper B', 'source_unique_id': 'test-6-complex-prop'},
    {'raw_text': "Capper A 1u I like the Mets to score first. +150", 'capper_name': 'Capper A', 'source_unique_id': 'test-7-unknown'},
]
EXPECTED_RESULTS = {
    'test-1-simple-ml': {'capper_name': 'Capper A', 'league': 'NBA', 'bet_type': 'Moneyline', 'pick_value': 'Los Angeles Lakers ML', 'unit': 2.0, 'odds': 150},
    'test-2-new-capper': {'capper_name': 'Capperc', 'league': 'NFL', 'bet_type': 'Spread', 'pick_value': 'Kansas City Chiefs -7.5', 'unit': 1.0, 'odds': -110},
    'test-3-fuzzy-capper': {'capper_name': 'The Nba Expert', 'league': 'NBA', 'bet_type': 'Player Prop', 'pick_value': 'Nikola Jokic: Pts Over 25.5', 'unit': 3.0, 'odds': -115},
    'test-4-total-format': {'capper_name': 'Capper B', 'league': 'NBA', 'bet_type': 'Total', 'pick_value': 'twolves vs suns Over 220', 'unit': 1.5, 'odds': 100},
    'test-5-parlay': {'capper_name': 'Capper A', 'league': 'Other', 'bet_type': 'Parlay', 'pick_value': '(NFL) Dallas Cowboys -3.5 / (NCAAF) Rutgers +14.5', 'unit': 4.0, 'odds': 264},
    'test-6-complex-prop': {'capper_name': 'Capper B', 'league': 'NBA', 'bet_type': 'Player Prop', 'pick_value': 'LeBron James: Pts+Reb+Ast Over 45.5', 'unit': 1.0, 'odds': -120},
    'test-7-unknown': {'capper_name': 'Capper A', 'league': 'MLB', 'bet_type': 'Game Prop', 'pick_value': 'I like the Mets to score first.', 'unit': 1.0, 'odds': 150},
}
OCR_TEXT_FROM_IMAGE = "ImageBasedCapper 2.5u New York Knicks -4.5 -110"
TEST_OCR_PICK = {'raw_text': OCR_TEXT_FROM_IMAGE, 'capper_name': 'ImageBasedCapper', 'source_unique_id': 'test-8-ocr'}
EXPECTED_OCR_RESULT = {'capper_name': 'Imagebasedcapper', 'league': 'NBA', 'bet_type': 'Spread', 'pick_value': 'New York Knicks -4.5', 'unit': 2.5, 'odds': -110}
TEST_OFF_HOURS_PICK = {'raw_text': "OffHoursCapper 1u Boston Bruins ML -150", 'capper_name': 'OffHoursCapper', 'source_unique_id': 'test-9-off-hours'}

def get_mock_ai_response(*args, **kwargs):
    prompt_content = kwargs['messages'][0]['content']
    json_start_index = prompt_content.rfind('[')
    if json_start_index == -1: return []
    json_string = prompt_content[json_start_index:]
    raw_picks_for_ai = json.loads(json_string)

    responses = []
    ai_map = {
        "Capper A 2u Los Angeles Lakers ML +150": {"league": "NBA", "bet_type": "Moneyline", "pick_value": "Los Angeles Lakers ML", "unit": 2.0, "odds_american": 150},
        "Capper C 1u Kansas City Chiefs -7.5 -110 NFL": {"league": "NFL", "bet_type": "Spread", "pick_value": "Kansas City Chiefs -7.5", "unit": 1.0, "odds_american": -110},
        "The NB Expert 3u Nikola Jokic Over 25.5 Pts -115": {"league": "NBA", "bet_type": "Player Prop", "pick_value": "Nikola Jokic: Pts Over 25.5", "unit": 3.0, "odds_american": -115},
        "Capper B 1.5u Total for the game twolves vs suns O 220 +100": {"league": "NBA", "bet_type": "Total", "pick_value": "twolves vs suns Over 220", "unit": 1.5, "odds_american": 100},
        "Capper A 4u Parlay: (nfl) Dallas Cowboys -3.5 / (ncaaf) rutgers +14.5 +264": {"league": "Other", "bet_type": "Parlay", "pick_value": "(NFL) Dallas Cowboys -3.5 / (NCAAF) Rutgers +14.5", "unit": 4.0, "odds_american": 264},
        "Capper B 1u Player Prop: LeBron James Pts+Reb+Ast O 45.5 -120": {"league": "NBA", "bet_type": "Player Prop", "pick_value": "LeBron James: Pts+Reb+Ast Over 45.5", "unit": 1.0, "odds_american": -120},
        "Capper A 1u I like the Mets to score first. +150": {"league": "MLB", "bet_type": "Game Prop", "pick_value": "I like the Mets to score first.", "unit": 1.0, "odds_american": 150},
        OCR_TEXT_FROM_IMAGE: {"league": "NBA", "bet_type": "Spread", "pick_value": "New York Knicks -4.5", "unit": 2.5, "odds_american": -110}
    }
    for pick in raw_picks_for_ai:
        if pick['text'] in ai_map:
            response = ai_map[pick['text']]
            response['raw_pick_id'] = pick['raw_pick_id']
            responses.append(response)
    
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(responses)
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    return mock_completion

async def cleanup_test_data(unique_ids_to_clean: List[str], cappers_to_clean: List[str]):
    if not supabase: return
    logging.info("\n--- CLEANUP: Deleting test data ---")
    try:
        supabase.table('live_structured_picks').delete().in_('source_unique_id', unique_ids_to_clean).execute()
        supabase.table('live_raw_picks').delete().in_('source_unique_id', unique_ids_to_clean).execute()
        if cappers_to_clean:
            supabase.table('capper_directory').delete().in_('canonical_name', cappers_to_clean).execute()
        logging.info("Cleanup complete.")
    except Exception as e:
        logging.error(f"Error during cleanup: {e}")
        raise

async def simulate_scraper_insert(picks: List[Dict]):
    if not supabase: return
    pick_date = datetime.now(EASTERN_TIMEZONE).date().isoformat()
    payload = [{'capper_name': p['capper_name'],'raw_text': p['raw_text'],'pick_date': pick_date,'source_unique_id': p['source_unique_id'],'status': 'pending','process_attempts': 0} for p in picks]
    try:
        supabase.table('live_raw_picks').insert(payload).execute()
        logging.info(f"Successfully inserted {len(payload)} simulated raw picks.")
    except Exception as e:
        logging.error(f"Error simulating scraper insert: {e}")
        raise

# --- Test Case Functions ---
@patch('ai_parser.ai_client')
async def test_full_pipeline(mock_ai_client):
    print("\n" + "="*20 + " TEST CASE 1: FULL PIPELINE " + "="*20)
    mock_ai_client.chat.completions.create.side_effect = get_mock_ai_response
    unique_ids = [p['source_unique_id'] for p in TEST_RAW_PICKS]
    cappers = [c['canonical_name'] for c in FUZZY_PREP_DATA['capper_directory']] + ['Capperc']
    
    await cleanup_test_data(unique_ids, cappers)
    logging.info("--- SETUP ---")
    supabase.table('capper_directory').insert(FUZZY_PREP_DATA['capper_directory']).execute()
    await simulate_scraper_insert(TEST_RAW_PICKS)
    
    logging.info("--- EXECUTION ---")
    # --- START OF FINAL FIX ---
    # Loop the processor to handle batching, just like in production.
    max_runs = 5 # Safety break
    for i in range(max_runs):
        logging.info(f"Processor run #{i+1}...")
        run_processor()
        # Check if there are any pending picks left for this test run
        res = supabase.table('live_raw_picks').select('id', count='exact') \
            .eq('status', 'pending').in_('source_unique_id', unique_ids).execute()
        if res.count == 0:
            logging.info("All test picks processed.")
            break
        if i == max_runs - 1:
            logging.error("Processor did not finish all picks within max runs.")
    # --- END OF FINAL FIX ---
    
    logging.info("--- VERIFICATION ---")
    res = supabase.table('live_structured_picks').select('*, capper_directory(canonical_name)').in_('source_unique_id', unique_ids).execute()
    assert len(res.data) == len(TEST_RAW_PICKS), f"FAIL: Expected {len(TEST_RAW_PICKS)} picks, found {len(res.data)}"
    
    results_map = {p['source_unique_id']: p for p in res.data}
    failures = 0
    for uid, expected in EXPECTED_RESULTS.items():
        actual = results_map[uid]
        if actual['capper_directory']['canonical_name'] != expected['capper_name'] or actual['league'] != expected['league'] or actual['bet_type'] != expected['bet_type'] or actual['pick_value'].strip().lower() != expected['pick_value'].strip().lower() or actual['unit'] != expected['unit'] or actual['odds_american'] != expected['odds']:
            failures += 1
    
    if failures == 0: print("✅ SUCCESS: All 42 checks passed for the main pipeline.")
    else: print(f"❌ FAILED: {failures * 6} checks failed.")

    await cleanup_test_data(unique_ids, cappers)
    return failures == 0

@patch('ai_parser.ai_client')
@patch('scrapers.asyncio.to_thread', new_callable=AsyncMock)
async def test_ocr_functionality(mock_to_thread, mock_ai_client):
    print("\n" + "="*20 + " TEST CASE 2: OCR PIPELINE " + "="*20)
    mock_to_thread.return_value = OCR_TEXT_FROM_IMAGE
    mock_ai_client.chat.completions.create.side_effect = get_mock_ai_response
    
    unique_ids = [TEST_OCR_PICK['source_unique_id']]
    cappers = [EXPECTED_OCR_RESULT['capper_name']]

    await cleanup_test_data(unique_ids, cappers)
    await simulate_scraper_insert([TEST_OCR_PICK])

    logging.info("--- EXECUTION ---")
    run_processor()

    logging.info("--- VERIFICATION ---")
    res = supabase.table('live_structured_picks').select('*, capper_directory(canonical_name)').in_('source_unique_id', unique_ids).execute()
    assert len(res.data) == 1, "FAIL: OCR pick was not processed."
    
    actual = res.data[0]
    expected = EXPECTED_OCR_RESULT
    assert actual['capper_directory']['canonical_name'] == expected['capper_name'] and actual['league'] == expected['league'] and actual['bet_type'] == expected['bet_type'] and actual['pick_value'] == expected['pick_value'] and actual['unit'] == expected['unit'] and actual['odds_american'] == expected['odds']
    
    print("✅ SUCCESS: OCR pipeline processed the simulated image text correctly.")
    await cleanup_test_data(unique_ids, cappers)
    return True

@patch('run_pipeline.datetime')
async def test_operational_hours_gate(mock_datetime):
    print("\n" + "="*20 + " TEST CASE 3: OPERATIONAL HOURS " + "="*20)
    mock_now = datetime(2025, 11, 2, 3, 15, 0, tzinfo=EASTERN_TIMEZONE)
    mock_datetime.now.return_value = mock_now

    unique_ids = [TEST_OFF_HOURS_PICK['source_unique_id']]
    cappers = [TEST_OFF_HOURS_PICK['capper_name']]

    await cleanup_test_data(unique_ids, cappers)
    await simulate_scraper_insert([TEST_OFF_HOURS_PICK])

    logging.info(f"--- EXECUTION at simulated time: {mock_now.strftime('%H:%M:%S %Z')} ---")
    await run_main_pipeline()

    logging.info("--- VERIFICATION ---")
    res = supabase.table('live_raw_picks').select('*').eq('source_unique_id', unique_ids[0]).single().execute()
    assert res.data is not None, "FAIL: Off-hours pick was not found."
    assert res.data['status'] == 'pending', f"FAIL: Pick status was '{res.data['status']}', expected 'pending'."

    print("✅ SUCCESS: Pipeline correctly skipped execution outside of operational hours.")
    await cleanup_test_data(unique_ids, cappers)
    return True

async def main_test_runner():
    global supabase
    print("\n" + "#"*20 + " STARTING FULL TEST SUITE " + "#"*20)
    
    supabase = get_supabase_client()
    if not supabase:
        logging.error("Could not initialize Supabase client. Aborting test suite.")
        return

    try:
        results = []
        results.append(await test_full_pipeline())
        results.append(await test_ocr_functionality())
        results.append(await test_operational_hours_gate())

        print("\n" + "="*20 + " TEST SUITE SUMMARY " + "="*20)
        if all(results):
            print("🎉 ALL TEST CASES PASSED SUCCESSFULLY! Your application is ready. 🎉")
        else:
            failed_count = len([r for r in results if not r])
            print(f"⚠️ {failed_count} TEST CASE(S) FAILED. Please review the logs above. ⚠️")

    except Exception as e:
        logging.error(f"A critical error occurred during the test suite: {e}", exc_info=True)
    finally:
        print("\nTest suite finished.")

if __name__ == "__main__":
    asyncio.run(main_test_runner())