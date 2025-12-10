import asyncio
import re
import logging
import os
import numpy as np
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Message

import config
from database import db
from models import RawPick

OCR_AVAILABLE = False
try:
    import pytesseract
    import cv2
    OCR_AVAILABLE = True
    # Check common paths or use PATH
    default_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(default_path):
        pytesseract.pytesseract.tesseract_cmd = default_path
except ImportError:
    pass

logger = logging.getLogger(__name__)

class TelegramScraper:
    def __init__(self):
        self.client = None
        if all([config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH, config.TELEGRAM_SESSION_NAME]):
            self.client = TelegramClient(
                StringSession(config.TELEGRAM_SESSION_NAME), 
                int(config.TELEGRAM_API_ID), 
                config.TELEGRAM_API_HASH
            )

    def _remove_watermark(self, img):
        try:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, np.array([0, 50, 50]), np.array([10, 255, 255])) + \
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
                for line in t.split('\n'):
                    l = line.strip()
                    if len(l) > 4 and re.search(r'[A-Z0-9]', l, re.I):
                        combined.add(l)
            
            final = "\n".join(sorted(list(combined)))
            return f"\n\n[OCR RESULT (Combines 3 Passes)]:\n{final}" if len(final) > 5 else ""
        except Exception: return ""

    async def _perform_ocr(self, message: Message) -> str:
        if not OCR_AVAILABLE or not message.photo: return ""
        try:
            data = await message.download_media(file=bytes)
            return await asyncio.to_thread(self._cpu_bound_ocr, data)
        except: return ""

    def _get_pick_regex(self):
        # Looks for Spread (-5, +3.5), Moneyline (ML, Pk), Totals (Over, Under), or Units (2u)
        return r"([+-]\d+\.?\d*|\b(ML|Pk|Pick'?em|Ev|Even)\b|\b(Over|Under|o|u)\s*\d+|\d+(\.\d+)?\s*u)"

    def _clean_capper_name(self, name: str) -> str:
        return re.sub(r'^[\W_]+|[\W_]+$', '', name).strip()

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
        if re.search(r'\b(VOID|CANCEL|REFUND|CORRECTION|LOSS|PUSH|GRADE|WON|LOST)\b', text, re.I): return False
        if re.search(r'(❌|💰|🚫|✅)', text): return False # Results usually have these
        
        # 3. Spam Filters (New)
        lower = text.lower()
        if "dm me" in lower or "join vip" in lower or "promo code" in lower:
            # If it's short and spammy, ignore it. 
            # If it's long, it might be a pick with a footer, so we keep it.
            if len(text) < 200: return False
            
        return True

    async def scrape(self):
        if not self.client: return
        try:
            await self.client.start()
            
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
                    
                    if last_scraped:
                        cutoff_utc = max(last_scraped, start_of_today_utc)
                        logger.info(f"🔄 Resuming {title} from {cutoff_utc}")
                    else:
                        cutoff_utc = start_of_today_utc
                        logger.info(f"📅 First run for {title}: Scanning from {cutoff_utc}")

                    latest_msg_date = None
                    
                    async for msg in self.client.iter_messages(entity, limit=None):
                        if msg.date <= cutoff_utc:
                            break 

                        if latest_msg_date is None:
                            latest_msg_date = msg.date
                        
                        text = (msg.text or "").strip()
                        ocr = await self._perform_ocr(msg)
                        full_text = f"{text}\n{ocr}".strip()
                        
                        if not self._is_valid_pick_message(full_text): continue

                        lines = [l.strip() for l in full_text.split('\n') if l.strip()]
                        capper = self._extract_capper_name(lines, title, channel_id)
                        
                        pick = RawPick(
                            source_unique_id=f"tg-{channel_id}-{msg.id}",
                            source_url=f"https://t.me/c/{channel_id}/{msg.id}",
                            capper_name=capper,
                            raw_text=full_text,
                            pick_date=msg.date.astimezone(tz).date()
                        )
                        db.upload_raw_pick(pick)
                    
                    new_checkpoint = latest_msg_date if latest_msg_date else run_start_time
                    db.update_checkpoint(channel_id, new_checkpoint)
                        
                except Exception as e:
                    logger.error(f"Error scraping {entity_id}: {e}")
        finally:
            await self.client.disconnect()

async def run_scrapers():
    s = TelegramScraper()
    await s.scrape()
