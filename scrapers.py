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

    # --- ADVANCED OCR LOGIC ---
    def _remove_watermark(self, img):
        # FILTERS OUT RED COLORS (Common in watermarks/live tags)
        try:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            # Range 1 for Red
            lower_red1 = np.array([0, 50, 50])
            upper_red1 = np.array([10, 255, 255])
            # Range 2 for Red
            lower_red2 = np.array([160, 50, 50])
            upper_red2 = np.array([180, 255, 255])
            
            mask = cv2.inRange(hsv, lower_red1, upper_red1) + cv2.inRange(hsv, lower_red2, upper_red2)
            
            # Dilate to cover edges
            kernel = np.ones((2,2), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=1)
            
            # Paint over the red areas with white
            img[mask > 0] = [255, 255, 255]
            return img
        except: return img

    def _cpu_bound_ocr(self, image_bytes: bytes) -> str:
        try:
            np_arr = np.frombuffer(image_bytes, np.uint8)
            original = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            # 1. UPSCALE (2.5x) - Critical for small text
            upscaled = cv2.resize(original, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
            
            processed_texts = []

            # PASS 1: Watermark Removed + Standard Threshold
            # Good for: Clean text with red noise
            clean_img = self._remove_watermark(upscaled.copy())
            gray_clean = cv2.cvtColor(clean_img, cv2.COLOR_BGR2GRAY)
            _, b1 = cv2.threshold(gray_clean, 180, 255, cv2.THRESH_BINARY)
            processed_texts.append(pytesseract.image_to_string(b1, config='--psm 6'))

            # PASS 2: Grayscale + Otsu Thresholding
            # Good for: Standard high contrast
            gray_raw = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
            _, b2 = cv2.threshold(gray_raw, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_texts.append(pytesseract.image_to_string(b2, config='--psm 6'))

            # PASS 3: INVERTED (Dark Mode)
            # Good for: White text on black background
            inverted = cv2.bitwise_not(gray_raw)
            _, b3 = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_texts.append(pytesseract.image_to_string(b3, config='--psm 6'))

            # COMBINE RESULTS
            unique_lines = set()
            for text in processed_texts:
                if not text: continue
                for line in text.split('\n'):
                    l = line.strip()
                    # Filter junk: Must have letters/numbers and be > 3 chars
                    if len(l) > 3 and re.search(r'[A-Z0-9]', l, re.I):
                        unique_lines.add(l)
            
            combined = "\n".join(sorted(list(unique_lines)))
            if len(combined) < 5: return ""
            
            return f"\n\n[OCR RESULT (Combines 3 Passes)]:\n{combined}"
        except Exception as e:
            logger.warning(f"OCR Internal Error: {e}")
            return ""

    async def _perform_ocr(self, message: Message) -> str:
        if not OCR_AVAILABLE or not message.photo: return ""
        try:
            data = await message.download_media(file=bytes)
            return await asyncio.to_thread(self._cpu_bound_ocr, data)
        except: return ""

    # --- PARSING HELPERS ---
    def _get_pick_regex(self):
        return r"([+-]\d+|\b(ML|Pk|Pick'?em|Ev|Even)\b|\b(Over|Under)\b|\d+(\.\d+)?\s*u)"

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
        if not re.search(self._get_pick_regex(), text, re.I): return False
        if re.search(r'\b(VOID|CANCEL|REFUND|CORRECTION|LOSS|PUSH|GRADE|WON|LOST)\b', text, re.I): return False
        if re.search(r'(❌|💰|🚫)', text): return False
        return True

    # --- MAIN LOGIC ---
    async def scrape(self):
        if not self.client: return
        try:
            await self.client.start()
            
            tz = ZoneInfo("US/Eastern")
            now_et = datetime.now(tz)
            start_of_today_et = now_et.replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_utc = start_of_today_et.astimezone(timezone.utc)
            
            logger.info(f"📅 STRICT WINDOW: Fetching picks after {cutoff_utc} (UTC)")

            for entity_id in config.TELEGRAM_CHANNELS:
                try:
                    try:
                        entity = await self.client.get_entity(entity_id)
                    except: continue

                    title = getattr(entity, 'title', 'Unknown')
                    
                    async for msg in self.client.iter_messages(entity, limit=None):
                        if msg.date < cutoff_utc:
                            break 
                        
                        text = (msg.text or "").strip()
                        ocr = await self._perform_ocr(msg)
                        full_text = f"{text}\n{ocr}".strip()
                        
                        if not self._is_valid_pick_message(full_text): continue

                        lines = [l.strip() for l in full_text.split('\n') if l.strip()]
                        capper = self._extract_capper_name(lines, title, getattr(entity, 'id', 0))
                        
                        pick = RawPick(
                            source_unique_id=f"tg-{getattr(entity, 'id', 0)}-{msg.id}",
                            source_url=f"https://t.me/c/{getattr(entity, 'id', 0)}/{msg.id}",
                            capper_name=capper,
                            raw_text=full_text,
                            pick_date=msg.date.astimezone(tz).date()
                        )
                        db.upload_raw_pick(pick)
                        
                except Exception as e:
                    logger.error(f"Error scraping {entity_id}: {e}")
        finally:
            await self.client.disconnect()

async def run_scrapers():
    s = TelegramScraper()
    await s.scrape()
