import os
import logging
from datetime import datetime, timedelta
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
        logging.info("Supabase client initialized for maintenance.")
    else:
        raise ConnectionError("Supabase credentials missing.")
except Exception as e:
    logging.error(f"Initialization failed: {e}")
    exit()

def run_maintenance():
    if not supabase:
        logging.error("Supabase client not available. Aborting maintenance.")
        return

    logging.info("Starting maintenance run to archive old pending picks...")
    try:
        threshold_time = (datetime.utcnow() - timedelta(hours=72)).isoformat()
        logging.info(f"Archiving pending picks created before: {threshold_time}")

        # Use the new 'live_structured_picks' table
        res = supabase.table('live_structured_picks') \
            .update({'result': 'archived'}) \
            .eq('result', 'pending') \
            .lt('created_at', threshold_time) \
            .execute()
        
        logging.info(f"Archive operation completed.")

    except Exception as e:
        logging.error(f"An error occurred during maintenance: {e}", exc_info=True)

    logging.info("Maintenance run finished.")

if __name__ == "__main__":
    run_maintenance()