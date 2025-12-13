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
from telethon.errors import SessionPasswordNeededError, AuthKeyError

import config
from database import db
from models import RawPick

OCR_AVAILABLE = False
try:
    import pytesseract
    import cv2
    OCR_AVAILABLE = True
    # Common windows path, adjust if needed
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
            # Mask out common watermark colors (light grey/white/semitransparent)
            mask = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 50, 255]))
            # Invert mask to keep text
            return img
        except: return img

    def _cpu_bound_ocr(self, image_bytes: bytes) -> str:
        try:
            np_arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None: return ""
            
            # Upscale
            img = cv2.resize(img, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
            
            # Preprocessing
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Multiple Thresholds for better capture
            _, b1 = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
            t1 = pytesseract.image_to_string(b1, config='--psm 6')
            
            _, b2 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            t2 = pytesseract.image_to_string(b2, config='--psm 6')

            inverted = cv2.bitwise_not(gray)
            _, b3 = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            t3 = pytesseract.image_to_string(b3, config='--psm 6')

            # Deduplicate lines
            combined = set()
            for t in [t1, t2, t3]:
                for line in t.split('\n'):
                    l = line.strip()
                    # Basic filter: must have letters/numbers and be > 4 chars
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
        # Catch Spreads, ML, Totals, Units
        return r"([+-]\d+\.?\d*|\b(ML|Pk|Pick'?em|Ev|Even)\b|\b(Over|Under|o|u)\s*\d+|\d+(\.\d+)?\s*u)"

    def _clean_capper_name(self, name: str) -> str:
        name = name.replace("[OCR RESULT (Combines 3 Passes)]:", "").strip()
        name = re.sub(r'^(from|source):?', '', name, flags=re.I)
        
        # Logic Fix: "30 @srcgroup << 2m ago" -> "srcgroup"
        name = re.sub(r'^\d+\s+', '', name) # Remove leading numbers
        name = re.sub(r'\s*«.*$', '', name) # Remove trailing timestamps
        
        # Logic Fix: "five (added)" -> "five"
        name = re.sub(r'\s*\([^)]*\)$', '', name)

        return re.sub(r'^[\W_]+|[\W_]+$', '', name).strip()

    def _is_invalid_name(self, name: str) -> bool:
        if len(name) < 2 or len(name) > 50: return True
        lower_name = name.lower()
        
        # Reject Matchups
        if re.search(r'\b(vs|over|under)\b', lower_name): return True
        
        # Reject Pure Numbers ("110")
        if re.match(r'^\d+$', name.strip()): return True
        # Reject Odds ("-110")
        if re.search(r'[-+]\d+', lower_name): return True
        # Reject Dates/Times
        if re.search(r'\d+/\d+|\d+:\d+', lower_name): return True
        
        # Reject Generic Terms
        if "combined reasoning" in lower_name or "ocr result" in lower_name: return True
        
        # Reject if name contains pick logic
        if re.search(self._get_pick_regex(), name, re.I): return True
        
        return False

    def _extract_capper_name(self, lines: list, channel_title: str, channel_id: int) -> str:
        # Filter raw lines first
        clean_lines = [l for l in lines if l.strip() and "[OCR RESULT" not in l and "Combines 3 Passes" not in l]
        is_aggregator = (channel_id in config.AGGREGATOR_CHANNEL_IDS) or ("CAPPERS" in channel_title.upper())
        
        # Default Fallback
        fallback_name = self._clean_capper_name(channel_title)
        
        # Force 'Unknown Capper' if channel name is purely generic
        if "CAPPERS" in fallback_name.upper() or "FREE PICKS" in fallback_name.upper():
            fallback_name = "Unknown Capper"
        else:
            # Clean "Free Picks" out of specific names (e.g. "Gold Boys Free Picks" -> "Gold Boys")
            fallback_name = re.sub(r'(free|capper|picks|locks|betting|official)', '', fallback_name, flags=re.I).strip()
            if len(fallback_name) < 2: fallback_name = "Unknown Capper"

        if not clean_lines: 
            return fallback_name

        if is_aggregator:
            # Check Line 1
            candidate = self._clean_capper_name(clean_lines[0])
            if candidate.startswith("@"):
                return candidate.replace("@", "").strip()
            
            if not self._is_invalid_name(candidate):
                if candidate.lower() not in config.BLACKLISTED_CAPPERS:
                    return candidate
            
            # Check Line 2
            if len(clean_lines) > 1:
                candidate_2 = self._clean_capper_name(clean_lines[1])
                if not self._is_invalid_name(candidate_2) and len(candidate_2) < 30:
                    return candidate_2

        return fallback_name

    def _is_valid_pick_message(self, text: str) -> bool:
        if not text: return False
        # Must contain pick keywords/numbers
        if not re.search(self._get_pick_regex(), text, re.I): return False
        # Reject Results/Grading messages
        if re.search(r'\b(VOID|CANCEL|REFUND|CORRECTION|LOSS|PUSH|GRADE|WON|LOST)\b', text, re.I): return False
        if re.search(r'(❌|💰|🚫|✅)', text): return False
        # Reject Spam
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
            
            tz = ZoneInfo("US/Eastern")
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
                    
                    if last_scraped and not force_full_day:
                        cutoff_utc = max(last_scraped, start_of_today_utc)
                    else:
                        cutoff_utc = start_of_today_utc

                    latest_msg_date = None
                    
                    async for msg in self.client.iter_messages(entity, limit=None):
                        if msg.date <= cutoff_utc: break 
                        if latest_msg_date is None: latest_msg_date = msg.date
                        
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
                    
                    if latest_msg_date:
                         db.update_checkpoint(channel_id, latest_msg_date)
                    elif not last_scraped:
                         db.update_checkpoint(channel_id, run_start_time)
                        
                except Exception as e:
                    logger.error(f"Error scraping {entity_id}: {e}")
        finally:
            if self.client.is_connected():
                await self.client.disconnect()

async def run_scrapers(force=False):
    s = TelegramScraper()
    await s.scrape(force_full_day=force)
