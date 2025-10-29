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
    """
    Archives old, ungraded picks to keep the 'pending' queue clean.
    - A pick is considered "old" if it's older than 72 hours.
    - It finds pending picks older than this threshold and updates their result to 'archived'.
    """
    if not supabase:
        logging.error("Supabase client not available. Aborting maintenance.")
        return

    logging.info("Starting maintenance run to archive old pending picks...")

    try:
        # Calculate the timestamp for 72 hours ago
        threshold_time = (datetime.utcnow() - timedelta(hours=72)).isoformat()
        
        logging.info(f"Archiving pending picks created before: {threshold_time}")

        # Find all pending picks created before the threshold and update their result to 'archived'
        res = supabase.table('live_picks') \
            .update({'result': 'archived'}) \
            .eq('result', 'pending') \
            .lt('created_at', threshold_time) \
            .execute()
        
        # The API response for an update doesn't typically give a count,
        # so we log that the operation was attempted. For a precise count, a SELECT would be needed first.
        logging.info(f"Archive operation completed. Check database for affected rows.")
        # If you need an exact count, you can uncomment the following block:
        #
        # count_res = supabase.table('live_picks').select('id', count='exact').eq('result', 'pending').lt('created_at', threshold_time).execute()
        # if count_res.count > 0:
        #     logging.info(f"Found {count_res.count} old pending picks to archive.")
        #     # ... then run the update ...
        #     logging.info("Archiving complete.")
        # else:
        #     logging.info("No old pending picks found to archive.")

    except Exception as e:
        logging.error(f"An error occurred during maintenance: {e}", exc_info=True)

    logging.info("Maintenance run finished.")

if __name__ == "__main__":
    run_maintenance()