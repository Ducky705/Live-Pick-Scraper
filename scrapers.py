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
    default_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(default_path):
        pytesseract.pytesseract.tesseract_cmd = default_path
except ImportError:
    pass

logger = logging.getLogger(__name__)

# IGNORE THESE HANDLES (Aggregators)
IGNORE_HANDLES = {'capperstree', 'cappersfree', 'cappers', 'free', 'picks', 'locks'}

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

    def _cpu_bound_ocr(self, image_bytes: bytes) -> str:
        try:
            np_arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None: return ""
            img = cv2.resize(img, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, b1 = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
            t1 = pytesseract.image_to_string(b1, config='--psm 6')
            final = t1.strip()
            return f"\n\n[OCR RESULT]:\n{final}" if len(final) > 5 else ""
        except Exception: return ""

    async def _perform_ocr(self, message: Message) -> str:
        if not OCR_AVAILABLE or not message.photo: return ""
        try:
            data = await message.download_media(file=bytes)
            return await asyncio.to_thread(self._cpu_bound_ocr, data)
        except: return ""

    def _get_pick_regex(self):
        return r"([+-]\d+\.?\d*|\b(ML|Pk|Pick'?em|Ev|Even)\b|\b(Over|Under|o|u)\s*\d+|\d+(\.\d+)?\s*u)"

    def _clean_name(self, name: str) -> str:
        name = re.sub(r'\[OCR RESULT.*?\]:?', '', name, flags=re.I)
        name = re.sub(r'^(source|credit|from|capper|pick by):', '', name, flags=re.I)
        name = re.sub(r'[^\w\s@&.\']', '', name) # Remove emojis
        name = re.sub(r'\s*«.*$', '', name) 
        return name.strip()

    def _is_invalid_name(self, name: str) -> bool:
        if len(name) < 2 or len(name) > 40: return True
        lower = name.lower()
        if re.search(r'\b(vs|over|under)\b', lower): return True
        if re.search(r'[-+]\d+', lower): return True 
        if re.search(r'\d+/\d+', lower): return True 
        if "ocr result" in lower or "combined reasoning" in lower: return True
        # Check against blacklist words
        if lower in {'picks', 'bet', 'game', 'today', 'free', 'lock'}: return True
        return False

    def _extract_capper_name(self, text: str, raw_original_text: str, channel_title: str, channel_id: int) -> str:
        """
        Hierarchical Name Extraction
        """
        # 1. MARKDOWN HEADER (Highest Priority)
        # Matches **CapperName** at start of message
        md_match = re.match(r'^\s*\*\*([^*\n]+)\*\*', raw_original_text)
        if md_match:
            candidate = self._clean_name(md_match.group(1))
            if not self._is_invalid_name(candidate):
                return candidate

        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        # 2. EXPLICIT SOURCE TAGS
        for line in lines:
            if re.match(r'^(source|credit|from|capper):', line, re.I):
                candidate = line.split(':', 1)[1].strip()
                clean = self._clean_name(candidate)
                if not self._is_invalid_name(clean):
                    return clean

        # 3. INTERNAL HANDLES (@name)
        # Scan lines for "@handle" but ignore common aggregators
        for line in lines:
            if '@' in line:
                words = line.split()
                for w in words:
                    if w.startswith('@'):
                        handle = w.replace('@', '').lower()
                        # Ignore aggregator handles
                        if any(bad in handle for bad in IGNORE_HANDLES):
                            continue
                        clean = self._clean_name(w)
                        if not self._is_invalid_name(clean):
                            return clean

        # 4. FIRST LINE (Aggregator Logic)
        # If channel is aggregator, check first 2 lines for a name
        is_aggregator = (channel_id in config.AGGREGATOR_CHANNEL_IDS) or ("CAPPERS" in channel_title.upper())
        if is_aggregator and lines:
            # Check Line 1
            line1 = self._clean_name(lines[0])
            if not self._is_invalid_name(line1) and not re.search(self._get_pick_regex(), line1):
                # Ignore generic headers
                if "cbb" not in line1.lower() and "nba" not in line1.lower():
                    return line1
            
            # Check Line 2 (Often Line 1 is "@capperstree")
            if len(lines) > 1:
                line2 = self._clean_name(lines[1])
                if not self._is_invalid_name(line2) and not re.search(self._get_pick_regex(), line2):
                     if "cbb" not in line2.lower() and "nba" not in line2.lower():
                        return line2

        # 5. FALLBACK: Channel Title
        fallback = self._clean_name(channel_title)
        cleaned_fallback = re.sub(r'(free|capper|picks|locks|betting|official|channel)', '', fallback, flags=re.I).strip()
        return cleaned_fallback if len(cleaned_fallback) > 2 else fallback

    def _is_valid_pick_message(self, text: str) -> bool:
        if not text: return False
        if not re.search(self._get_pick_regex(), text, re.I): return False
        if re.search(r'\b(VOID|CANCEL|REFUND|CORRECTION|LOSS|PUSH|GRADE|WON|LOST)\b', text, re.I): return False
        if re.search(r'(❌|💰|🚫|✅)', text): return False
        lower = text.lower()
        if "dm me" in lower or "join vip" in lower or "promo code" in lower:
            if len(text) < 200: return False
        return True

    async def scrape(self, force_full_day=False):
        if not self.client:
            logger.warning("Telegram Client not initialized.")
            return

        try:
            try:
                await self.client.start()
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
                    
                    cutoff_utc = start_of_today_utc if force_full_day or not last_scraped else max(last_scraped, start_of_today_utc)
                    latest_msg_date = None
                    
                    async for msg in self.client.iter_messages(entity, limit=None):
                        if msg.date <= cutoff_utc: break 
                        if latest_msg_date is None: latest_msg_date = msg.date
                        
                        text = (msg.text or "").strip()
                        ocr = await self._perform_ocr(msg)
                        full_text = f"{text}\n{ocr}".strip()
                        
                        if not self._is_valid_pick_message(full_text): continue

                        # Pass raw original text for Markdown Header detection
                        capper = self._extract_capper_name(full_text, msg.text or "", title, channel_id)
                        
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
