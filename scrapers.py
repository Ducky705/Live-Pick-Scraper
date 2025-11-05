# File: ./scrapers.py
import asyncio
import re
import logging
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.sessions import StringSession

import config

from database import upload_raw_pick

# --- OCR Imports (Conditional) ---
OCR_AVAILABLE = False
try:
    import pytesseract, cv2, numpy as np
    pytesseract.get_tesseract_version() 
    OCR_AVAILABLE = True
    logging.info("Tesseract OCR engine found. Image processing is enabled.")
except Exception as e:
    logging.warning(f"Tesseract or related library not found or failed: {e}. OCR will be disabled.")

def perform_ocr(image_bytes: bytes) -> str:
    """Performs OCR on a byte stream of an image."""
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
    """Scrapes recent messages from configured Telegram channels for potential picks."""
    if not all([config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH, config.TELEGRAM_SESSION_NAME, config.TELEGRAM_CHANNELS]):
        logging.warning("Telegram scraper not fully configured. Skipping.")
        return

    client = TelegramClient(StringSession(config.TELEGRAM_SESSION_NAME), int(config.TELEGRAM_API_ID), config.TELEGRAM_API_HASH)
    
    try:
        await client.start()
        logging.info("Telegram client started.")
        
        after_time_utc = datetime.now(timezone.utc) - timedelta(hours=config.SCRAPE_WINDOW_HOURS)
        logging.info(f"Searching for messages AFTER (UTC): {after_time_utc.strftime('%Y-%m-%d %H:%M:%S')}")

        for channel_entity in config.TELEGRAM_CHANNELS:
            try:
                entity = await client.get_entity(channel_entity)
                channel_title = getattr(entity, 'title', str(channel_entity)) 
                logging.info(f"Scraping Telegram channel: {channel_title}")
                
                async for message in client.iter_messages(entity, limit=500, offset_date=datetime.now(timezone.utc)):
                    if message.date < after_time_utc:
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

                    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                    if not lines: continue

                    separator_index = -1
                    for i, line in enumerate(lines):
                        if '➖➖➖➖➖' in line:
                            separator_index = i
                            break
                    
                    content_lines = lines[:separator_index] if separator_index != -1 else lines
                    if not content_lines: continue

                    # --- START OF FIX: Improved Capper Name Parsing Logic ---
                    
                    # Heuristic: Check if message matches 'Capper Name' then 'Pick Details' format
                    is_aggregator_format = False
                    if len(content_lines) > 1:
                        first_line = content_lines[0]
                        second_line = content_lines[1]
                        third_line = content_lines[2] if len(content_lines) > 2 else ""
                        
                        # A more robust regex to identify lines containing betting information.
                        pick_terms_regex = r'([+-]\d{3,}|ML|[+-]\d{1,2}\.?5|[OU]\d|\d+[\.,]?\d*\s*u(nit)?s?)'
                        
                        # A line is likely a capper name if it's short and lacks betting terms...
                        first_line_is_clean = (
                            len(first_line) < 40 and 
                            not re.search(pick_terms_regex, first_line, re.I)
                        )
                        # Check second line first, then third line if second is empty (common in aggregator format).
                        second_line_has_pick = re.search(pick_terms_regex, second_line, re.I)
                        third_line_has_pick = not second_line_has_pick and second_line.strip() == "" and re.search(pick_terms_regex, third_line, re.I)

                        if first_line_is_clean and (second_line_has_pick or third_line_has_pick):
                            is_aggregator_format = True


                    # --- Determine Capper Name and Pick Body based on the format ---
                    if is_aggregator_format:
                        # Format matches "Capper Name\nPick". Use the first line as the capper.
                        # This correctly handles both configured and misconfigured aggregator channels.
                        parsed_capper_name = content_lines[0]
                        pick_body_lines = content_lines[1:]
                        logging.info(f"Heuristic success: Parsed capper '{parsed_capper_name}' from message in '{channel_title}'.")
                    elif entity.id in config.AGGREGATOR_CHANNEL_IDS:
                        # It's a known aggregator but doesn't match the format. Skip to avoid misattribution.
                        logging.warning(f"Skipping message {message.id} in aggregator '{channel_title}': Does not match expected 'Capper\\nPick' format.")
                        continue
                    else:
                        # It's a regular channel and doesn't match the format. Use the channel name as the capper.
                        parsed_capper_name = channel_title
                        pick_body_lines = content_lines

                    cleaned_capper_name = parsed_capper_name.strip('*- _')
                    # --- END OF FIX ---
                    
                    final_text_content = "\n".join(pick_body_lines)
                    
                    if not final_text_content:
                        continue 
                    
                    positive_keywords = r'([+-]\d{3,}|ML|[+-]\d{1,2}\.?5|\d+\.?\d*u(nit)?\b)'
                    negative_keywords = r'\b(VOID|CANCEL|REFUND|CORRECTION|LOSS|PUSH|GRADE|WON|LOST|SWEEP)\b'
                    
                    if re.search(positive_keywords, final_text_content, re.I) and not re.search(negative_keywords, final_text_content, re.I):
                        source_url = f"https://t.me/{entity.username}/{message.id}" if hasattr(entity, 'username') else str(channel_entity)
                        unique_id = f"telegram-{entity.id}-{message.id}"
                        pick_date_et = message.date.astimezone(config.EASTERN_TIMEZONE)
                        
                        upload_raw_pick({
                            'capper_name': cleaned_capper_name, 
                            'raw_text': final_text_content,   
                            'pick_date': pick_date_et.date().isoformat(),
                            'source_url': source_url,
                            'source_unique_id': unique_id,
                            'status': config.PICK_STATUS_PENDING
                        })
            except Exception as e:
                logging.error(f"Error scraping Telegram channel '{channel_entity}': {e}")
    finally:
        if client.is_connected():
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
    asyncio.run(run_scrapers())