# File: ./database.py
import logging
from datetime import datetime, timedelta
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, PICK_STATUS_PENDING, PICK_STATUS_ARCHIVED

# --- Global Cache ---
capper_directory_cache = None
supabase: Client = None

def get_supabase_client() -> Client:
    """Initializes and returns a Supabase client, or None on failure."""
    global supabase
    if supabase:
        return supabase
    try:
        if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            logging.info("Supabase client initialized.")
            return supabase
        else:
            logging.error("Supabase credentials missing in config.")
            return None
    except Exception as e:
        logging.error(f"Failed to initialize Supabase client: {e}")
        return None

def increment_raw_pick_attempts(pick_ids: list):
    """Increments the process_attempts counter for a list of raw picks."""
    db = get_supabase_client()
    if not db or not pick_ids: return
    try:
        db.rpc('increment_process_attempts', {'pick_ids': pick_ids}).execute()
        logging.warning(f"Incremented process_attempts for {len(pick_ids)} raw picks after a failure.")
    except Exception as e:
        logging.error(f"Error incrementing raw pick attempts: {e}")

def get_pending_raw_picks(limit: int = 5, max_attempts: int = 3):
    """Fetches a batch of pending raw picks that have not exceeded the max attempt count."""
    db = get_supabase_client()
    if not db: return []
    try:
        response = db.table('live_raw_picks').select('*') \
            .eq('status', PICK_STATUS_PENDING) \
            .lt('process_attempts', max_attempts) \
            .limit(limit).execute()
        return response.data if response.data else []
    except Exception as e:
        logging.error(f"Error fetching pending raw picks: {e}")
        return []

def upload_raw_pick(pick_data: dict):
    """Inserts a raw pick if its source_unique_id is not already present."""
    db = get_supabase_client()
    if not db: return

    unique_id = pick_data.get('source_unique_id')
    if not unique_id:
        logging.warning(f"Skipping pick because it has no unique ID: {pick_data.get('raw_text', '')[:50]}...")
        return
        
    try:
        res = db.table('live_raw_picks').select('id', count='exact').eq('source_unique_id', unique_id).execute()
        
        if res.count > 0:
            logging.info(f"Duplicate pick found based on unique ID '{unique_id}'. Skipping.")
            return
            
        db.table('live_raw_picks').insert(pick_data).execute()
        logging.info(f"Uploaded new raw pick with unique ID '{unique_id}'.")
        
    except Exception as e:
        if 'duplicate key value violates unique constraint' in str(e):
             logging.info(f"Database rejected duplicate pick with unique ID '{unique_id}'. Skipping.")
        else:
             logging.error(f"Error uploading raw pick with unique ID '{unique_id}': {e}")

def update_raw_picks_status(pick_ids: list, status: str):
    """Updates the status of a list of raw picks by their IDs."""
    db = get_supabase_client()
    if not db or not pick_ids: return
    try:
        db.table('live_raw_picks').update({'status': status}).in_('id', pick_ids).execute()
        logging.info(f"Updated status to '{status}' for {len(pick_ids)} raw picks.")
    except Exception as e:
        logging.error(f"Error updating raw pick statuses: {e}")

def insert_structured_picks(picks: list):
    """Inserts a list of structured picks into the database."""
    db = get_supabase_client()
    if not db or not picks: return
    try:
        db.table('live_structured_picks').insert(picks).execute()
        logging.info(f"Inserted {len(picks)} new structured picks.")
    except Exception as e:
        logging.error(f"Error inserting structured picks: {e}")

def get_or_create_capper(capper_name: str, fuzz_processor) -> int:
    """Finds a capper by name (with fuzzy matching) or creates a new one."""
    global capper_directory_cache
    db = get_supabase_client()
    if not db or not capper_name:
        logging.warning("Capper name is empty, cannot process.")
        return None

    try:
        normalized_name = ' '.join(capper_name.strip().split()).title()
        
        res = db.table('capper_directory').select('id').eq('canonical_name', normalized_name).limit(1).execute()
        if res.data:
            return res.data[0]['id']

        if capper_directory_cache is None:
            all_cappers_res = db.table('capper_directory').select('id, canonical_name').execute()
            capper_directory_cache = all_cappers_res.data if all_cappers_res.data else []

        if capper_directory_cache:
            capper_map = {c['canonical_name']: c['id'] for c in capper_directory_cache}
            if capper_map:
                best_match, score = fuzz_processor.extractOne(normalized_name, capper_map.keys())
                # --- START OF FIX #1 ---
                # Increased threshold to 95 to prevent incorrect matches like 'Capperc' -> 'Capper C'
                if score > 95:
                # --- END OF FIX #1 ---
                    logging.info(f"Found close fuzzy match for '{normalized_name}': '{best_match}'. Using existing capper.")
                    return capper_map[best_match]
        
        logging.info(f"Creating new capper: '{normalized_name}'")
        insert_res = db.table('capper_directory').insert({'canonical_name': normalized_name}).execute()
        
        if insert_res.data and 'id' in insert_res.data[0]:
            new_id = insert_res.data[0]['id']
            capper_directory_cache = None
            logging.info(f"Successfully created capper '{normalized_name}' with ID: {new_id}")
            return new_id
        else:
            logging.error(f"Failed to create or retrieve ID for new capper: '{normalized_name}'. Response: {insert_res.data}")
            return None
            
    except Exception as e:
        logging.error(f"Error in get_or_create_capper for '{capper_name}': {e}")
        return None

def run_maintenance_archive(archive_threshold_hours: int):
    """Archives pending structured picks older than the specified threshold."""
    db = get_supabase_client()
    if not db:
        logging.error("Supabase client not available. Aborting maintenance.")
        return

    logging.info("Starting maintenance run to archive old pending picks...")
    try:
        threshold_time = (datetime.utcnow() - timedelta(hours=archive_threshold_hours)).isoformat()
        logging.info(f"Archiving pending picks created before: {threshold_time}")

        db.table('live_structured_picks') \
            .update({'result': PICK_STATUS_ARCHIVED}) \
            .eq('result', PICK_STATUS_PENDING) \
            .lt('created_at', threshold_time) \
            .execute()
        
        logging.info("Archive operation completed.")
    except Exception as e:
        logging.error(f"An error occurred during maintenance: {e}", exc_info=True)