import os
import asyncio
import logging
import json
import hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
from telethon import TelegramClient

# --- Import Pipeline Functions ---
from processing_service import run_processor
# We will copy the 'upload_raw_pick' function directly into this test
# to ensure it's testing the exact logic in isolation.
from scrapers import perform_ocr 

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

# --- Client Initializations ---
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_SESSION_NAME = os.getenv('TELEGRAM_SESSION_NAME')
TARGET_CHANNEL_STR = os.getenv('TELEGRAM_CHANNEL_URLS', '').split(',')[0].strip()

supabase: Client = None
try:
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logging.info("Supabase client initialized.")
    else:
        raise ConnectionError("Supabase credentials missing.")
except Exception as e:
    logging.error(f"Initialization failed: {e}")
    exit()

# --- Copied function from scrapers.py to test directly ---
def upload_raw_pick(pick_data: dict):
    if not supabase: return
    
    unique_id = pick_data.get('source_unique_id')
    if not unique_id:
        logging.warning(f"Skipping pick because it has no unique ID: {pick_data.get('raw_text', '')[:50]}...")
        return
        
    try:
        res = supabase.table('raw_picks').select('id', count='exact').eq('source_unique_id', unique_id).execute()
        
        if res.count > 0:
            logging.info(f"Duplicate pick found based on unique ID '{unique_id}'. Skipping.")
            return
            
        supabase.table('raw_picks').insert(pick_data).execute()
        logging.info(f"Uploaded new raw pick with unique ID '{unique_id}'.")
        
    except Exception as e:
        if 'duplicate key value violates unique constraint' in str(e):
             logging.info(f"Database rejected duplicate pick with unique ID '{unique_id}'. Skipping.")
        else:
             logging.error(f"Error uploading raw pick with unique ID '{unique_id}': {e}")


async def get_latest_image_message_from_telegram(client: TelegramClient, channel_entity):
    logging.info(f"Searching for the latest message in '{getattr(channel_entity, 'title', channel_entity)}'...")
    async for message in client.iter_messages(channel_entity, limit=100):
        if message.text or message.photo:
            logging.info(f"Found a suitable test message with ID: {message.id}")
            return message
    logging.warning("No suitable test message found in the last 100 messages.")
    return None

async def main():
    if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_NAME, TARGET_CHANNEL_STR]):
        logging.error("Telegram credentials missing. Aborting test.")
        return

    from telethon.sessions import StringSession
    client = TelegramClient(StringSession(TELEGRAM_SESSION_NAME), int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
    
    test_raw_pick_id = None
    created_live_pick_ids = []
    unique_id_to_test = None
    
    try:
        # ==================== 1. FETCH TEST DATA ====================
        print("\n" + "="*20 + " 1. FETCH TEST DATA " + "="*20)
        await client.start()
        entity = await client.get_entity(int(TARGET_CHANNEL_STR) if TARGET_CHANNEL_STR.lstrip('-').isdigit() else TARGET_CHANNEL_STR)
        message = await get_latest_image_message_from_telegram(client, entity)
        if not message: return

        text_content = (message.text or "").strip()
        if message.photo:
            image_bytes = await message.download_media(file=bytes)
            ocr_text = await asyncio.to_thread(perform_ocr, image_bytes) if image_bytes else ""
            text_content += f"\n{ocr_text}".strip()
        
        unique_id_to_test = f"telegram-{entity.id}-{message.id}"
        
        # *** FIX: Explicitly set the 'status' to 'pending' to match what the processor expects ***
        test_pick_data = {
            'capper_name': text_content.split('\n')[0].strip(),
            'raw_text': text_content,
            'pick_date': message.date.date().isoformat(),
            'source_unique_id': unique_id_to_test,
            'status': 'pending' 
        }
        logging.info(f"Test data prepared with unique ID: {unique_id_to_test}")

        # ==================== 2. TEST INSERTION LOGIC ====================
        print("\n" + "="*20 + " 2. TEST INSERTION LOGIC " + "="*20)
        
        logging.info("--- 2a. First Insertion Attempt ---")
        upload_raw_pick(test_pick_data)
        
        res = supabase.table('raw_picks').select('id').eq('source_unique_id', unique_id_to_test).single().execute()
        if res.data and res.data['id']:
            test_raw_pick_id = res.data['id']
            logging.info(f"SUCCESS: Pick inserted successfully with raw_pick_id: {test_raw_pick_id}")
        else:
            logging.error("FAILURE: Pick was not found in database after first insertion attempt.")
            raise Exception("Initial insertion failed")

        logging.info("\n--- 2b. Duplicate Insertion Attempt ---")
        upload_raw_pick(test_pick_data)
        
        count_res = supabase.table('raw_picks').select('id', count='exact').eq('source_unique_id', unique_id_to_test).execute()
        if count_res.count == 1:
            logging.info("SUCCESS: Deduplication logic is working correctly. The duplicate was skipped.")
        else:
            logging.error(f"FAILURE: Found {count_res.count} records for the same unique ID. Deduplication failed.")
            raise Exception("Deduplication test failed")

        # ==================== 3. RUN & VERIFY PROCESSOR ====================
        print("\n" + "="*20 + " 3. RUN & VERIFY PROCESSOR " + "="*20)
        run_processor()
        logging.info("Processing service finished.")
        
        status_res = supabase.table('raw_picks').select('status').eq('id', test_raw_pick_id).single().execute()
        if status_res.data['status'] == 'processed':
            logging.info(f"SUCCESS: Raw pick ID {test_raw_pick_id} status updated to 'processed'.")
        else:
            logging.error(f"FAILURE: Raw pick status is '{status_res.data['status']}'.")

        five_minutes_ago = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
        live_picks_res = supabase.table('live_picks').select('id').gte('created_at', five_minutes_ago).execute()
        created_live_pick_ids = [p['id'] for p in live_picks_res.data]
        if created_live_pick_ids:
             logging.info(f"SUCCESS: Found {len(created_live_pick_ids)} new pick(s) in 'live_picks' table.")

    except Exception as e:
        logging.error(f"An error occurred during the test: {e}", exc_info=True)
    finally:
        # ==================== 4. CLEANUP DATABASE ====================
        print("\n" + "="*20 + " 4. CLEANUP DATABASE " + "="*20)
        if test_raw_pick_id:
            logging.info(f"Cleaning up raw pick ID: {test_raw_pick_id}")
            supabase.table('raw_picks').delete().eq('id', test_raw_pick_id).execute()
        
        if created_live_pick_ids:
            logging.info(f"Cleaning up {len(created_live_pick_ids)} live pick(s) with IDs: {created_live_pick_ids}")
            supabase.table('live_picks').delete().in_('id', created_live_pick_ids).execute()
        
        logging.info("Cleanup complete.")
        
        if client.is_connected():
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())