import os
import sys

# ==============================================================================
# FILE CONTENT DEFINITIONS
# ==============================================================================

SCRAPERS_PY = """import asyncio
import re
import logging
import os
import numpy as np
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Message
from telethon.errors import SessionPasswordNeededError, AuthKeyError

import config
from database import db
from models import RawPick

OCR_AVAILABLE = False
try:
    import pytesseract
    import cv2
    OCR_AVAILABLE = True
    # Check common paths or use PATH
    default_path = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
    if os.path.exists(default_path):
        pytesseract.pytesseract.tesseract_cmd = default_path
except ImportError:
    pass

logger = logging.getLogger(__name__)

class TelegramScraper:
    def __init__(self):
        self.client = None
        if all([config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH, config.TELEGRAM_SESSION_NAME]):
            try:
                self.client = TelegramClient(
                    StringSession(config.TELEGRAM_SESSION_NAME), 
                    int(config.TELEGRAM_API_ID), 
                    config.TELEGRAM_API_HASH
                )
            except Exception as e:
                logger.error(f"Failed to initialize Telegram Client: {e}")
                self.client = None

    def _remove_watermark(self, img):
        try:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, np.array([0, 50, 50]), np.array([10, 255, 255])) + \\
                   cv2.inRange(hsv, np.array([160, 50, 50]), np.array([180, 255, 255]))
            kernel = np.ones((2,2), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=1)
            img[mask > 0] = [255, 255, 255]
            return img
        except: return img

    def _cpu_bound_ocr(self, image_bytes: bytes) -> str:
        try:
            np_arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None: return ""
            
            img = cv2.resize(img, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
            
            clean = self._remove_watermark(img)
            gray = cv2.cvtColor(clean, cv2.COLOR_BGR2GRAY)
            
            _, b1 = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
            t1 = pytesseract.image_to_string(b1, config='--psm 6')
            
            _, b2 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            t2 = pytesseract.image_to_string(b2, config='--psm 6')

            inverted = cv2.bitwise_not(gray)
            _, b3 = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            t3 = pytesseract.image_to_string(b3, config='--psm 6')

            combined = set()
            for t in [t1, t2, t3]:
                for line in t.split('\\n'):
                    l = line.strip()
                    if len(l) > 4 and re.search(r'[A-Z0-9]', l, re.I):
                        combined.add(l)
            
            final = "\\n".join(sorted(list(combined)))
            return f"\\n\\n[OCR RESULT (Combines 3 Passes)]:\\n{final}" if len(final) > 5 else ""
        except Exception: return ""

    async def _perform_ocr(self, message: Message) -> str:
        if not OCR_AVAILABLE or not message.photo: return ""
        try:
            data = await message.download_media(file=bytes)
            return await asyncio.to_thread(self._cpu_bound_ocr, data)
        except: return ""

    def _get_pick_regex(self):
        # Looks for Spread (-5, +3.5), Moneyline (ML, Pk), Totals (Over, Under), or Units (2u)
        return r"([+-]\\d+\\.?\\d*|\\b(ML|Pk|Pick'?em|Ev|Even)\\b|\\b(Over|Under|o|u)\\s*\\d+|\\d+(\\.\\d+)?\\s*u)"

    def _clean_capper_name(self, name: str) -> str:
        return re.sub(r'^[\\W_]+|[\\W_]+$', '', name).strip()

    def _extract_capper_name(self, lines: list, channel_title: str, channel_id: int) -> str:
        is_aggregator = (channel_id in config.AGGREGATOR_CHANNEL_IDS) or ("CAPPERS FREE" in channel_title.upper())
        if not lines: return "Unknown Capper"

        if is_aggregator:
            candidate = self._clean_capper_name(lines[0].strip())
            is_blacklisted = candidate.lower() in config.BLACKLISTED_CAPPERS
            is_pick = re.search(self._get_pick_regex(), candidate, re.I)
            if candidate and not is_blacklisted and not is_pick:
                return candidate

        clean = channel_title
        for bad in config.BLACKLISTED_CAPPERS:
            clean = re.sub(re.escape(bad), '', clean, flags=re.I)
        return self._clean_capper_name(clean) or "Unknown Capper"

    def _is_valid_pick_message(self, text: str) -> bool:
        if not text: return False
        
        # 1. Must contain pick-like numbers or keywords
        if not re.search(self._get_pick_regex(), text, re.I): return False
        
        # 2. Explicit Exclusions (Grading, Results, Spam)
        if re.search(r'\\b(VOID|CANCEL|REFUND|CORRECTION|LOSS|PUSH|GRADE|WON|LOST)\\b', text, re.I): return False
        if re.search(r'(❌|💰|🚫|✅)', text): return False # Results usually have these
        
        # 3. Spam Filters (New)
        lower = text.lower()
        if "dm me" in lower or "join vip" in lower or "promo code" in lower:
            if len(text) < 200: return False
            
        return True

    async def scrape(self, force_full_day=False):
        if not self.client:
            logger.warning("Telegram Client not initialized. Skipping scrape.")
            return

        try:
            try:
                await self.client.start()
            except (SessionPasswordNeededError, AuthKeyError, ValueError) as e:
                logger.error(f"❌ Authentication failed (Invalid Session): {e}")
                return
            except Exception as e:
                logger.error(f"❌ Connection failed: {e}")
                return
            
            try:
                tz = ZoneInfo("US/Eastern")
            except Exception:
                tz = timezone(timedelta(hours=-5))

            now_et = datetime.now(tz)
            start_of_today_et = now_et.replace(hour=0, minute=0, second=0, microsecond=0)
            start_of_today_utc = start_of_today_et.astimezone(timezone.utc)
            
            run_start_time = datetime.now(timezone.utc)

            for entity_id in config.TELEGRAM_CHANNELS:
                try:
                    try:
                        entity = await self.client.get_entity(entity_id)
                    except: continue

                    title = getattr(entity, 'title', 'Unknown')
                    channel_id = getattr(entity, 'id', 0)
                    
                    last_scraped = db.get_last_checkpoint(channel_id)
                    
                    if last_scraped and last_scraped.tzinfo is None:
                        last_scraped = last_scraped.replace(tzinfo=timezone.utc)
                    
                    # LOGIC: If force_full_day is True, we ignore the checkpoint and start from 00:00 Today.
                    # Otherwise, we use the checkpoint (efficient).
                    if last_scraped and not force_full_day:
                        cutoff_utc = max(last_scraped, start_of_today_utc)
                        logger.info(f"🔄 Resuming {title} from {cutoff_utc}")
                    else:
                        cutoff_utc = start_of_today_utc
                        logger.info(f"📅 Full Day Scan for {title}: Scanning from {cutoff_utc}")

                    latest_msg_date = None
                    
                    async for msg in self.client.iter_messages(entity, limit=None):
                        if msg.date <= cutoff_utc:
                            break 

                        if latest_msg_date is None:
                            latest_msg_date = msg.date
                        
                        text = (msg.text or "").strip()
                        ocr = await self._perform_ocr(msg)
                        full_text = f"{text}\\n{ocr}".strip()
                        
                        if not self._is_valid_pick_message(full_text): continue

                        lines = [l.strip() for l in full_text.split('\\n') if l.strip()]
                        capper = self._extract_capper_name(lines, title, channel_id)
                        
                        pick = RawPick(
                            source_unique_id=f"tg-{channel_id}-{msg.id}",
                            source_url=f"https://t.me/c/{channel_id}/{msg.id}",
                            capper_name=capper,
                            raw_text=full_text,
                            pick_date=msg.date.astimezone(tz).date()
                        )
                        db.upload_raw_pick(pick)
                    
                    # Only update checkpoint if we actually found a newer message
                    if latest_msg_date:
                         db.update_checkpoint(channel_id, latest_msg_date)
                    elif not last_scraped:
                         # If it was a first run and no messages, set checkpoint to now so we don't scan forever next time
                         db.update_checkpoint(channel_id, run_start_time)
                        
                except Exception as e:
                    logger.error(f"Error scraping {entity_id}: {e}")
        finally:
            if self.client.is_connected():
                await self.client.disconnect()

async def run_scrapers(force=False):
    s = TelegramScraper()
    await s.scrape(force_full_day=force)
"""

MAIN_PY = """import asyncio
import logging
import argparse
import sys
from datetime import datetime

import config
from scrapers import run_scrapers
from processing_service import process_picks
from database import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_pipeline(force=False):
    logger.info("🚀 STARTING SNIPER PIPELINE")
    
    # --- PHASE 1: SCRAPE TODAY'S PICKS ---
    try:
        logger.info(f"📡 Checking Telegram (Force Full Day: {force})...")
        await run_scrapers(force=force)
    except Exception as e:
        logger.error(f"❌ Scraper Crashed: {e}")
        sys.exit(1)

    # --- PHASE 2: EFFICIENCY CHECK ---
    # Check if there is ANY work to do.
    try:
        pending_picks = db.get_pending_raw_picks(limit=1)
        if not pending_picks:
            logger.info("🛑 No new picks & no pending retries. SHUTTING DOWN.")
            sys.exit(0) # Exit with success code
    except Exception as e:
        logger.error(f"Error checking DB status: {e}")

    # --- PHASE 3: PROCESS BATCHES ---
    logger.info("🧠 Work detected! Running AI Processor...")
    try:
        # FIX: Reduced batch count from 5 to 2 to prevent GitHub Action timeouts.
        # Previous runs took ~2 mins per batch, causing 10m+ runs which get cancelled.
        for i in range(2): 
            if not db.get_pending_raw_picks(limit=1):
                break
            process_picks()
            await asyncio.sleep(1) 
    except Exception as e:
        logger.error(f"❌ Processor Crashed: {e}")

    # --- PHASE 4: CLEANUP ---
    try:
        db.archive_old_picks(config.ARCHIVE_AFTER_HOURS)
    except: pass

    logger.info("🏁 Pipeline Finished")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Force re-scrape of the entire day (00:00 ET)")
    args = parser.parse_args()
    asyncio.run(run_pipeline(force=args.force))
"""

SCRAPE_AND_PROCESS_YML = """name: Sniper Pick Scraper

on:
  # 1. Manual Trigger with Options
  workflow_dispatch:
    inputs:
      force_scrape:
        description: 'Force Full Day Scrape (Ignore Checkpoints)'
        required: false
        default: false
        type: boolean

  # 2. Register changes immediately when you push to main
  push:
    branches: ["main"]
  
  # 3. DYNAMIC SCHEDULE BLOCK (Managed by scheduler.py)
  schedule:
    - cron: '0 14-23,0-4 * * *'
    - cron: '15,30,45 21-23 * * 1-5'
    - cron: '15,30,45 15-20 * * 0,6'

permissions:
  contents: read
  actions: write

jobs:
  run-sniper:
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - name: Check out code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip' 

      - name: Install System Dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y tesseract-ocr libtesseract-dev

      - name: Install Python Dependencies
        run: |
          pip install -r requirements.txt

      - name: Run Pipeline
        env:
          TELEGRAM_API_ID: ${{ secrets.TELEGRAM_API_ID }}
          TELEGRAM_API_HASH: ${{ secrets.TELEGRAM_API_HASH }}
          TELEGRAM_SESSION_NAME: ${{ secrets.TELEGRAM_SESSION_NAME }}
          TELEGRAM_CHANNEL_URLS: ${{ secrets.TELEGRAM_CHANNEL_URLS }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
          AI_PARSER_MODEL: ${{ secrets.AI_PARSER_MODEL }}
        run: |
          # Logic:
          # 1. If triggered manually with checkbox checked -> Run with --force
          # 2. If triggered by Schedule or Push -> Run normally (incremental)
          
          if [[ "${{ github.event.inputs.force_scrape }}" == "true" ]]; then
            echo "⚠️ MANUAL OVERRIDE: Forcing Full Day Scrape..."
            python main.py --force
          else
            echo "⚡ Standard Run: Incremental Scrape..."
            python main.py
          fi
"""

# ==============================================================================
# EXECUTION
# ==============================================================================

def write_file(path, content):
    # Ensure directory exists
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Created/Updated: {path}")

def main():
    print("🚀 Applying Force Logic & YAML Updates...")
    
    files_to_write = {
        "scrapers.py": SCRAPERS_PY,
        "main.py": MAIN_PY,
        ".github/workflows/scrape_and_process.yml": SCRAPE_AND_PROCESS_YML
    }

    for path, content in files_to_write.items():
        write_file(path, content)

    print("\n🎉 All files updated successfully!")
    print("👉 Now run: git add . && git commit -m 'Add Force Scrape Logic' && git push")

if __name__ == "__main__":
    main()