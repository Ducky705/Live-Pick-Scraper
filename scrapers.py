import os
import asyncio
import re
import logging
import hashlib
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo  # <-- REPLACED pytz
from dotenv import load_dotenv
from supabase import create_client, Client
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- OCR Imports ---
OCR_AVAILABLE = False
try:
    import pytesseract, cv2, numpy as np
    from PIL import Image
    pytesseract.get_tesseract_version() 
    OCR_AVAILABLE = True
    logging.info("Tesseract OCR engine found and ready. Image processing is enabled.")
except (ImportError, ModuleNotFoundError) as e:
    logging.warning(f"An OCR library is not installed ({e}). OCR for images will be disabled.")
except Exception as e:
    logging.warning(f"Tesseract OCR engine not found or failed to initialize: {e}. OCR for images will be disabled.")

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

# Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# Telegram
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_SESSION_NAME = os.getenv('TELEGRAM_SESSION_NAME')
raw_telegram_channels = [url.strip() for url in os.getenv('TELEGRAM_CHANNEL_URLS', '').split(',') if url.strip()]
TELEGRAM_CHANNELS = []
for channel in raw_telegram_channels:
    try:
        TELEGRAM_CHANNELS.append(int(channel))
    except ValueError:
        TELEGRAM_CHANNELS.append(channel)

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
except Exception as e:
    logging.error(f"Failed to initialize Supabase client: {e}")
    supabase = None

def upload_raw_pick(pick_data: dict):
    if not supabase: return
    
    unique_id = pick_data.get('source_unique_id')
    if not unique_id:
        logging.warning(f"Skipping pick because it has no unique ID: {pick_data.get('raw_text', '')[:50]}...")
        return
        
    try:
        res = supabase.table('live_raw_picks').select('id', count='exact').eq('source_unique_id', unique_id).execute()
        
        if res.count > 0:
            logging.info(f"Duplicate pick found based on unique ID '{unique_id}'. Skipping.")
            return
            
        supabase.table('live_raw_picks').insert(pick_data).execute()
        logging.info(f"Uploaded new raw pick with unique ID '{unique_id}'.")
        
    except Exception as e:
        if 'duplicate key value violates unique constraint' in str(e):
             logging.info(f"Database rejected duplicate pick with unique ID '{unique_id}'. Skipping.")
        else:
             logging.error(f"Error uploading raw pick with unique ID '{unique_id}': {e}")


def perform_ocr(image_bytes: bytes) -> str:
    if not OCR_AVAILABLE or not image_bytes: return ""
    try:
        np_arr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if image is None: return ""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        processed_image = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(processed_image, config=custom_config)
        return text.strip()
    except Exception as e:
        logging.error(f"OCR processing failed: {e}")
        return ""

async def scrape_telegram():
    if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_NAME, TELEGRAM_CHANNELS]):
        logging.warning("Telegram scraper not fully configured. Skipping.")
        return

    EASTERN_TIMEZONE = ZoneInfo('US/Eastern') # <-- UPDATED

    client = TelegramClient(StringSession(TELEGRAM_SESSION_NAME), int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
    await client.start()
    logging.info("Telegram client started.")
    
    after_time = datetime.now(timezone.utc) - timedelta(hours=48)
    logging.info(f"Searching for messages AFTER (UTC): {after_time.strftime('%Y-%m-%d %H:%M:%S')}")

    for channel_entity in TELEGRAM_CHANNELS:
        try:
            entity = await client.get_entity(channel_entity)
            logging.info(f"Scraping Telegram channel: {getattr(entity, 'title', channel_entity)}")
            
            async for message in client.iter_messages(entity, limit=500, offset_date=datetime.now(timezone.utc)):
                if message.date < after_time:
                    logging.info(f"Message {message.id} is older than the search window. Stopping search for this channel.")
                    break

                text_content = (message.text or "").strip()
                if OCR_AVAILABLE and message.photo:
                    image_bytes = await message.download_media(file=bytes)
                    if image_bytes:
                        ocr_text = await asyncio.to_thread(perform_ocr, image_bytes)
                        if ocr_text: text_content += f"\n\n--- OCR TEXT ---\n{ocr_text}"
                
                text_content = text_content.strip()
                if not text_content: continue

                if re.search(r'([+-]\d{3,}|ML|[+-]\d{1,2}\.?5|\d+\.?d*u(nit)?\b)', text_content, re.I):
                    capper_name = text_content.strip().split('\n')[0].strip()
                    source_url = f"https://t.me/{entity.username}/{message.id}" if hasattr(entity, 'username') else str(channel_entity)
                    unique_id = f"telegram-{entity.id}-{message.id}"
                    
                    pick_date_et = message.date.astimezone(EASTERN_TIMEZONE)
                    
                    upload_raw_pick({
                        'capper_name': capper_name,
                        'raw_text': text_content,
                        'pick_date': pick_date_et.date().isoformat(),
                        'source_url': source_url,
                        'source_unique_id': unique_id,
                        'status': 'pending'
                    })
        except Exception as e:
            logging.error(f"Error scraping Telegram channel '{channel_entity}': {e}")
    
    await client.disconnect()
    logging.info("Telegram client disconnected.")

async def run_scrapers():
    """Main function to run all scrapers."""
    logging.info("Starting scraper run...")
    
    tasks = [scrape_telegram()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            logging.error(f"A scraper task failed: {result}")
        
    logging.info("Scraper run finished.")

if __name__ == "__main__":
    logging.info("Running scrapers.py directly for testing...")
    asyncio.run(run_scrapers())