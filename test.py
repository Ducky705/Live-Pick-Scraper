import os
import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # <-- REPLACED pytz
from dotenv import load_dotenv
from supabase import create_client, Client

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

# --- Client Initializations ---
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

supabase: Client = None
try:
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logging.info("Supabase client initialized for timezone test.")
    else:
        raise ConnectionError("Supabase credentials missing.")
except Exception as e:
    logging.error(f"Initialization failed: {e}")
    exit()

async def run_timezone_test():
    """
    This test specifically verifies that the timezone conversion for pick_date is correct.
    It simulates a late-night pick in Eastern Time and ensures it's not assigned to the next day.
    """
    print("\n" + "="*20 + " RUNNING TIMEZONE FIX TEST " + "="*20)
    
    unique_id_for_test = f"timezone-test-{int(datetime.now().timestamp())}"
    test_record_id = None
    
    try:
        # ==================== 1. SETUP TEST CASE ====================
        print("\n--- 1. Setting up test case ---")
        # Use the modern zoneinfo library
        EASTERN_TIMEZONE = ZoneInfo('US/Eastern') # <-- UPDATED
        UTC_TIMEZONE = ZoneInfo('UTC')           # <-- UPDATED
        
        # Define the "correct" date we expect to see in the database.
        correct_et_date = datetime.now(EASTERN_TIMEZONE).date()
        
        # Create a datetime object for 11:30 PM on that date in Eastern Time.
        late_night_et = datetime(
            correct_et_date.year,
            correct_et_date.month,
            correct_et_date.day,
            23, 30, 0, tzinfo=EASTERN_TIMEZONE
        )
        
        # Convert it to UTC to simulate the raw timestamp from Telethon.
        simulated_utc_time = late_night_et.astimezone(UTC_TIMEZONE) # <-- UPDATED
        
        logging.info(f"Correct Expected Date (ET): {correct_et_date.isoformat()}")
        logging.info(f"Simulating pick time (ET):   {late_night_et.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logging.info(f"Equivalent time in UTC:     {simulated_utc_time.strftime('%Y-%m-%d %H:%M:%S %Z')} <-- Note the date has advanced.")

        # ==================== 2. SIMULATE SCRAPER LOGIC ====================
        print("\n--- 2. Simulating scraper's date conversion and DB insert ---")
        
        # This is the *exact* logic from the fixed scrapers.py
        processed_date_object = simulated_utc_time.astimezone(EASTERN_TIMEZONE).date()
        final_date_iso = processed_date_object.isoformat()
        
        logging.info(f"Applying fix: Converting UTC time back to ET and getting the date...")
        logging.info(f"Resulting date to be saved: {final_date_iso}")
        
        test_pick_data = {
            'raw_text': 'Timezone Test Pick',
            'pick_date': final_date_iso,
            'source_unique_id': unique_id_for_test,
            'status': 'pending'
        }
        
        insert_res = supabase.table('live_raw_picks').insert(test_pick_data).execute()
        test_record_id = insert_res.data[0]['id']
        logging.info(f"Test record inserted into 'live_raw_picks' with ID: {test_record_id}")

        # ==================== 3. VERIFICATION ====================
        print("\n--- 3. Verifying the stored date ---")
        
        verify_res = supabase.table('live_raw_picks').select('pick_date').eq('id', test_record_id).single().execute()
        
        stored_date_str = verify_res.data['pick_date']
        logging.info(f"Date retrieved from database: {stored_date_str}")
        
        if stored_date_str == correct_et_date.isoformat():
            print("\n✅ SUCCESS: The date stored in the database is the correct Eastern Time date.")
        else:
            print(f"\n❌ FAILURE: The stored date ({stored_date_str}) does NOT match the expected ET date ({correct_et_date.isoformat()}).")

    except Exception as e:
        logging.error(f"An error occurred during the test: {e}", exc_info=True)
    finally:
        # ==================== 4. CLEANUP ====================
        print("\n--- 4. Cleaning up test data ---")
        if test_record_id:
            logging.info(f"Deleting test record with ID: {test_record_id}")
            supabase.table('live_raw_picks').delete().eq('id', test_record_id).execute()
            logging.info("Cleanup complete.")
        else:
            logging.warning("No test record ID was created, skipping cleanup.")
        
        print("\n" + "="*20 + " TIMEZONE TEST FINISHED " + "="*20)


if __name__ == "__main__":
    # Rename your test file to test_timezone_fix.py and run it
    asyncio.run(run_timezone_test())