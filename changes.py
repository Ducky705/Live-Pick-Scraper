import os

# ==============================================================================
# 1. SCRAPERS.PY (Fixes: Capper Name Extraction, "110" Bug, Parentheses Cleanup)
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
    # Common windows path, adjust if needed
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
                for line in t.split('\\n'):
                    l = line.strip()
                    # Basic filter: must have letters/numbers and be > 4 chars
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
        # Catch Spreads, ML, Totals, Units
        return r"([+-]\\d+\\.?\\d*|\\b(ML|Pk|Pick'?em|Ev|Even)\\b|\\b(Over|Under|o|u)\\s*\\d+|\\d+(\\.\\d+)?\\s*u)"

    def _clean_capper_name(self, name: str) -> str:
        name = name.replace("[OCR RESULT (Combines 3 Passes)]:", "").strip()
        name = re.sub(r'^(from|source):?', '', name, flags=re.I)
        
        # Logic Fix: "30 @srcgroup << 2m ago" -> "srcgroup"
        name = re.sub(r'^\\d+\\s+', '', name) # Remove leading numbers
        name = re.sub(r'\\s*«.*$', '', name) # Remove trailing timestamps
        
        # Logic Fix: "five (added)" -> "five"
        name = re.sub(r'\\s*\\([^)]*\\)$', '', name)

        return re.sub(r'^[\\W_]+|[\\W_]+$', '', name).strip()

    def _is_invalid_name(self, name: str) -> bool:
        if len(name) < 2 or len(name) > 50: return True
        lower_name = name.lower()
        
        # Reject Matchups
        if re.search(r'\\b(vs|over|under)\\b', lower_name): return True
        
        # Reject Pure Numbers ("110")
        if re.match(r'^\\d+$', name.strip()): return True
        # Reject Odds ("-110")
        if re.search(r'[-+]\\d+', lower_name): return True
        # Reject Dates/Times
        if re.search(r'\\d+/\\d+|\\d+:\\d+', lower_name): return True
        
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
        if re.search(r'\\b(VOID|CANCEL|REFUND|CORRECTION|LOSS|PUSH|GRADE|WON|LOST)\\b', text, re.I): return False
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
"""

# ==============================================================================
# 2. DATABASE.PY (Fixes: Strict Name Validation, Smart Aliasing)
# ==============================================================================
DATABASE_PY = """import logging
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Any
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential

import config
from models import RawPick, StandardizedPick

logger = logging.getLogger(__name__)

# --- SMART ALIAS MAPPING ---
CAPPER_ALIASES = {
    "big al": "bigalmcmordie",
    "al mcmordie": "bigalmcmordie",
    "alan mcmordie": "bigalmcmordie",
    "doc sports": "docsports",
    "docs sports": "docsports",
    "scott sprietzer": "scottspreitzer",
    "scott spreitzer": "scottspreitzer",
    "vernon croy": "vernoncroy",
    "vc": "vernoncroy",
    "tony george": "tonygeorge",
    "jason sharpe": "jasonsharpe",
    "strike point": "strikepointsports",
    "sps": "strikepointsports",
    "ferringo": "robertferringo",
    "robert ferringo": "robertferringo",
    "indian cowboy": "indiancowboy",
    "ic": "indiancowboy",
    "vegas mirabe": "vegasmirabet",
    "vegas mira": "vegasmirabet"
}

class DatabaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        try:
            if config.SUPABASE_URL and config.SUPABASE_KEY:
                self.client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
                self.capper_cache = {}
            else:
                logger.error("Supabase credentials missing.")
                self.client = None
        except Exception as e:
            logger.error(f"Failed to init Supabase: {e}")
            self.client = None

    def get_last_checkpoint(self, channel_id: int) -> Optional[datetime]:
        if not self.client: return None
        try:
            res = self.client.table('scraper_checkpoints').select('last_scraped_at').eq('channel_id', channel_id).execute()
            if res.data:
                return datetime.fromisoformat(res.data[0]['last_scraped_at'])
            return None
        except Exception:
            return None

    def update_checkpoint(self, channel_id: int, timestamp: datetime):
        if not self.client: return
        try:
            self.client.table('scraper_checkpoints').upsert({
                'channel_id': channel_id,
                'last_scraped_at': timestamp.isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def upload_raw_pick(self, pick: RawPick) -> bool:
        if not self.client: return False
        try:
            data = pick.model_dump(exclude={'id', 'process_attempts', 'created_at'})
            data['pick_date'] = data['pick_date'].isoformat()
            self.client.table('live_raw_picks').upsert(data, on_conflict='source_unique_id', ignore_duplicates=True).execute()
            return True
        except Exception: return False

    def get_pending_raw_picks(self, limit: int = 10) -> List[RawPick]:
        if not self.client: return []
        try:
            yesterday_iso = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            response = self.client.table('live_raw_picks').select('*') \\
                .eq('status', 'pending') \\
                .lt('process_attempts', 3) \\
                .gt('created_at', yesterday_iso) \\
                .order('created_at', desc=True) \\
                .limit(limit).execute()
            return [RawPick(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error fetching picks: {e}")
            return []

    def _normalize_key(self, name: str) -> str:
        if not name: return ""
        clean = name.lower()
        noise_words = ['vip', 'picks', 'locks', 'plays', 'sports', 'betting', 'consulting', 'capper', 'official', 'premium']
        for word in noise_words:
            clean = clean.replace(word, '')
        clean = re.sub(r'[^a-z0-9]', '', clean)
        return clean

    def _clean_display_name(self, name: str) -> str:
        clean = re.sub(r'[^\\x00-\\x7F]+', '', name)
        clean = re.sub(r'^[\\W_]+|[\\W_]+$', '', clean)
        return clean.strip()

    def get_or_create_capper(self, name: str, fuzzer) -> Optional[int]:
        if not self.client or not name: return None
        
        display_name = self._clean_display_name(name)
        
        # --- STRICT VALIDATION ---
        if len(display_name) < 2: return None 
        if re.search(r'\\b(vs|over|under)\\b', display_name, re.I):
            logger.warning(f"⚠️ Rejected invalid capper name (Matchup): {display_name}")
            return None 
        if re.match(r'^[-+]?\\d+(\\.\\d+)?$', display_name):
            logger.warning(f"⚠️ Rejected invalid capper name (Numeric): {display_name}")
            return None

        normalized_key = self._normalize_key(display_name)
        if not normalized_key: return None

        # Smart Alias Check
        if normalized_key in CAPPER_ALIASES:
            normalized_key = CAPPER_ALIASES[normalized_key]

        # Populate Cache
        if not self.capper_cache:
            try:
                res = self.client.table('capper_directory').select('id, canonical_name').limit(10000).execute()
                for item in res.data:
                    key = self._normalize_key(item['canonical_name'])
                    if key:
                        self.capper_cache[key] = item['id']
                    self.capper_cache[item['canonical_name']] = item['id']
            except Exception as e:
                logger.error(f"Failed to populate capper cache: {e}")

        # Exact Match
        if normalized_key in self.capper_cache:
            return self.capper_cache[normalized_key]

        # Fuzzy Match
        try:
            if self.capper_cache:
                existing_keys = list(self.capper_cache.keys())
                best_match, score = fuzzer.extractOne(normalized_key, existing_keys)
                
                if score >= 88:
                    matched_id = self.capper_cache[best_match]
                    logger.info(f"✨ Fuzzy matched '{display_name}' to existing ({best_match}) - Score: {score}")
                    self.capper_cache[normalized_key] = matched_id
                    return matched_id

            # Create New
            logger.info(f"🆕 Creating NEW Capper: {display_name}")
            res = self.client.table('capper_directory').insert({'canonical_name': display_name}).execute()
            if res.data:
                new_id = res.data[0]['id']
                self.capper_cache[normalized_key] = new_id
                self.capper_cache[display_name] = new_id
                return new_id
            
            return None

        except Exception as e:
            logger.error(f"❌ Error in capper lookup/creation: {e}")
            return None

    def insert_structured_picks(self, picks: List[StandardizedPick]):
        if not self.client or not picks: return
        try:
            data = []
            for p in picks:
                d = p.model_dump(exclude={'result'})
                d['pick_date'] = d['pick_date'].isoformat()
                data.append(d)
            self.client.table('live_structured_picks').insert(data).execute()
            logger.info(f"✅ Saved {len(picks)} picks.")
        except Exception as e:
            logger.error(f"Error saving: {e}")

    def update_raw_status(self, ids: List[int], status: str):
        if not self.client or not ids: return
        try:
            self.client.table('live_raw_picks').update({'status': status}).in_('id', ids).execute()
        except Exception: pass

    def increment_attempts(self, ids: List[int]):
        if not self.client or not ids: return
        try:
            for pick_id in ids:
                 self.client.rpc('increment_process_attempts', {'pick_ids': [pick_id]}).execute()
        except Exception:
             for pick_id in ids:
                res = self.client.table('live_raw_picks').select('process_attempts').eq('id', pick_id).execute()
                if res.data:
                    current = res.data[0].get('process_attempts', 0)
                    self.client.table('live_raw_picks').update({'process_attempts': current + 1}).eq('id', pick_id).execute()

    def archive_old_picks(self, hours: int):
        if not self.client: return
        threshold = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        try:
            self.client.table('live_structured_picks').update({'result': 'archived'}).eq('result', 'pending').lt('created_at', threshold).execute()
        except: pass

db = DatabaseManager()
"""

# ==============================================================================
# 3. PROCESSING_SERVICE.PY (Fixes: Unknown Capper ID Lookup)
# ==============================================================================
PROCESSING_SERVICE_PY = """import logging
import time
import re
from difflib import SequenceMatcher
from typing import List, Set, Tuple
from thefuzz import process as fuzz_process

from database import db
from models import StandardizedPick
import simple_parser
import ai_parser
import standardizer

logger = logging.getLogger(__name__)

# Terms found in betting app screenshots that are NOT picks
UI_NOISE_TERMS = [
    "deposit", "balance", "cash out", "bet slip", "total payout", 
    "potential payout", "wager", "to win", "accepted", "id:", 
    "bets placed", "my bets", "share my bet", "book a bet",
    "login", "sign up", "forgot password", "face id", "touch id",
    "combines 3 passes", "ocr result", "making money as usual",
    "see less", "bankroll", "unit =", "units =", "ecapper", "capper:",
    "betslip", "parlay", "teaser", "straight", "risk", "win"
]

def clean_ocr_garbage(text: str) -> str:
    if not text: return ""
    
    # Remove headers
    text = text.replace("[OCR RESULT (Combines 3 Passes)]:", "")
    
    lines = text.split('\\n')
    valid_lines = []
    prev_line = ""
    
    for line in lines:
        stripped = line.strip()
        lower_line = stripped.lower()
        
        # 1. Skip very short lines
        if len(stripped) < 3: continue 
        
        # 2. Skip Sportsbook UI Noise
        if any(term in lower_line for term in UI_NOISE_TERMS):
            continue

        # 3. Fuzzy Consecutive Deduplication
        if prev_line:
            similarity = SequenceMatcher(None, prev_line, stripped).ratio()
            if similarity > 0.85:
                continue
        
        # 4. Alphanumeric Density Check
        alpha_num = sum(c.isalnum() for c in stripped)
        total = len(stripped)
        if total > 0 and (alpha_num / total) < 0.5:
            continue
            
        valid_lines.append(stripped)
        prev_line = stripped
        
    return "\\n".join(valid_lines)

def get_existing_pick_signatures(capper_ids: List[int], dates: List[str]) -> Set[Tuple[int, str, str, str]]:
    if not db.client or not capper_ids:
        return set()
    try:
        date_strs = [d.isoformat() if hasattr(d, 'isoformat') else str(d) for d in dates]
        response = db.client.table('live_structured_picks') \\
            .select('capper_id, pick_date, pick_value, bet_type') \\
            .in_('capper_id', capper_ids) \\
            .in_('pick_date', date_strs) \\
            .execute()
        existing = set()
        for item in response.data:
            sig = (item['capper_id'], item['pick_date'], item['pick_value'], item['bet_type'])
            existing.add(sig)
        return existing
    except Exception as e:
        logger.error(f"Failed to fetch existing picks: {e}")
        return set()

def process_picks():
    start_time = time.time()
    
    # Increase batch size slightly for efficiency
    raw_picks = db.get_pending_raw_picks(limit=10)
    if not raw_picks: 
        print("💤 No pending picks found in DB.")
        return

    print(f"\\n📥 PROCESSING BATCH: {len(raw_picks)} Messages")

    to_standardize = []
    ai_batch = []
    processed_ids = []

    for pick in raw_picks:
        # 1. Clean Text
        clean_text = clean_ocr_garbage(pick.raw_text)
        pick.raw_text = clean_text 
        
        if len(clean_text) < 5: 
            processed_ids.append(pick.id)
            continue

        # 2. Hybrid Strategy: Regex First
        simple_picks = simple_parser.parse_with_regex(pick)
        
        if simple_picks:
            print(f"   ⚡ Regex found {len(simple_picks)} picks in ID {pick.id}")
            for sp in simple_picks:
                to_standardize.append((sp, pick))
            processed_ids.append(pick.id)
        else:
            # 3. Fallback to AI
            print(f"   🤖 Regex failed for ID {pick.id}, queueing for AI...")
            ai_batch.append(pick)

    # 4. Run AI Batch
    if ai_batch:
        try:
            ai_results = ai_parser.parse_with_ai(ai_batch)
            for parsed in ai_results:
                orig = next((p for p in ai_batch if p.id == parsed.raw_pick_id), None)
                if orig:
                    to_standardize.append((parsed, orig))
                    if orig.id not in processed_ids:
                        processed_ids.append(orig.id)
            
            for p in ai_batch:
                if p.id not in processed_ids: processed_ids.append(p.id)

        except Exception as e:
            logger.error(f"AI batch failed: {e}")
            failed_ids = [p.id for p in ai_batch]
            db.increment_attempts(failed_ids)
            processed_ids = [pid for pid in processed_ids if pid not in failed_ids]

    # 5. Standardize & Deduplicate
    potential_picks = []
    involved_capper_ids = []
    involved_dates = []

    # Cache "Unknown Capper" ID to avoid repeated DB calls
    unknown_capper_id = None

    for parsed, raw in to_standardize:
        # Dynamic Capper Lookup
        capper_id = db.get_or_create_capper(raw.capper_name, fuzz_process)
        
        if not capper_id:
            # If still None, get/create 'Unknown Capper' dynamically
            if not unknown_capper_id:
                unknown_capper_id = db.get_or_create_capper("Unknown Capper", fuzz_process)
            capper_id = unknown_capper_id

        # League & Bet Type Standardization
        std_league = standardizer.standardize_league(parsed.league)
        if std_league == 'Other':
            std_league = standardizer.infer_league(parsed.pick_value)

        std_type = standardizer.standardize_bet_type(parsed.bet_type)
        std_val = standardizer.format_pick_value(parsed.pick_value, std_type, std_league)

        std = StandardizedPick(
            capper_id=capper_id,
            pick_date=raw.pick_date,
            league=std_league,
            pick_value=std_val,
            bet_type=std_type,
            unit=parsed.unit,
            odds_american=parsed.odds_american,
            source_url=raw.source_url,
            source_unique_id=raw.source_unique_id
        )
        potential_picks.append(std)
        involved_capper_ids.append(capper_id)
        involved_dates.append(raw.pick_date)

    if potential_picks:
        existing_sigs = get_existing_pick_signatures(list(set(involved_capper_ids)), list(set(involved_dates)))
        final_picks = []
        seen_in_batch = set()

        for p in potential_picks:
            p_date_str = p.pick_date.isoformat() if hasattr(p.pick_date, 'isoformat') else str(p.pick_date)
            sig = (p.capper_id, p_date_str, p.pick_value, p.bet_type)
            
            if sig in existing_sigs: continue
            if sig in seen_in_batch: continue

            final_picks.append(p)
            seen_in_batch.add(sig)

        if final_picks:
            db.insert_structured_picks(final_picks)
            print(f"✅ Inserted {len(final_picks)} unique picks into DB.")
        else:
            print("✅ All picks were duplicates.")

    if processed_ids:
        db.update_raw_status(processed_ids, 'processed')
    
    print(f"⏱️  Batch finished in {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    process_picks()
"""

# ==============================================================================
# 4. MAIN.PY (Fixes: Resilience against scraper crash)
# ==============================================================================
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
    # We purposefully catch errors here so Processing (Phase 3) still runs
    try:
        logger.info(f"📡 Checking Telegram (Force Full Day: {force})...")
        await run_scrapers(force=force)
    except Exception as e:
        logger.error(f"❌ Scraper Crashed: {e}")

    # --- PHASE 2: EFFICIENCY CHECK ---
    try:
        pending_picks = db.get_pending_raw_picks(limit=1)
        if not pending_picks:
            logger.info("🛑 No new picks & no pending retries. SHUTTING DOWN.")
            sys.exit(0)
    except Exception as e:
        logger.error(f"Error checking DB status: {e}")

    # --- PHASE 3: PROCESS BATCHES ---
    logger.info("🧠 Work detected! Running AI Processor...")
    try:
        # Run 2 batches max to respect GitHub Action limits
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

# ==============================================================================
# 5. SIMPLE_PARSER.PY (Fixes: Hype Stripping)
# ==============================================================================
SIMPLE_PARSER_PY = """import re
import logging
from typing import Optional, List
from models import ParsedPick, RawPick
import standardizer

logger = logging.getLogger(__name__)

# 1. Units
RE_UNIT = re.compile(r'\\b(?P<val>\\d+(\\.\\d+)?)\\s*(u|unit|star)s?\\b|\\((?P<val_paren>\\d+(\\.\\d+)?)(u|unit)?\\)\\s*$', re.IGNORECASE)

# 2. Odds
RE_ODDS = re.compile(r'(?<!\\d)([-+]?\\d{3,})(?!\\d)')

# 3. League Headers
RE_LEAGUE_HEADER = re.compile(r'^\\(?(NFL|NBA|NHL|MLB|NCAAF|NCAAB|UFC|EPL)\\)?:?$', re.IGNORECASE)

# 4. Hype Terms
HYPE_TERMS = [
    "LOCK OF THE CENTURY", "WHALE PLAY", "MAX BET", "HAMMER", "BOMB", "NUKE",
    "INSIDER INFO", "FIXED", "GUARANTEED", "FREE PICK", "SYSTEM PLAY",
    "VIP", "POD", "POTD", "🔥", "💰", "🔒", "🚨", "✅"
]

PATTERNS = [
    {
        'type': 'Total',
        're': re.compile(r"^(?P<dir>o|u|over|under)\\s*(?P<line>\\d+(\\.\\d+)?)\\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{dir} {line}"
    },
    {
        'type': 'Player Prop', 
        're': re.compile(r"^(?P<name>.+?)\\s+(?P<dir>over|under|o|u)\\s*(?P<line>\\d+(\\.\\d+)?)\\s*(?P<stat>[a-zA-Z\\s]+)?(?P<odds_part>.*)$", re.I),
        'val_fmt': "{name} {dir} {line} {stat}"
    },
    {
        'type': 'Moneyline',
        're': re.compile(r"^(?P<team>.+?)\\s+(?:ML|Moneyline|M/L)\\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{team} ML"
    },
    {
        'type': 'Spread',
        're': re.compile(r"^(?!over|under|o\\s|u\\s)(?P<team>.{2,}?)\\s+(?P<spread>[-+]\\d+(\\.\\d+)?|Pk|Pick'em|Ev)\\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{team} {spread}"
    }
]

def _clean_hype_text(text: str) -> str:
    text = text.upper()
    for term in HYPE_TERMS:
        text = text.replace(term, "")
    text = re.sub(r'[!*]', '', text)
    return text.strip()

def _extract_unit(text: str) -> Optional[float]:
    if not text: return None
    m = RE_UNIT.search(text)
    if m:
        val = m.group('val') or m.group('val_paren')
        try: return float(val)
        except: pass
    lower = text.lower()
    if 'max' in lower or 'whale' in lower: return 5.0
    if 'pod' in lower or 'potd' in lower: return 3.0
    return None

def _extract_odds(text: str) -> Optional[int]:
    if not text: return None
    matches = RE_ODDS.findall(text)
    for m in matches:
        try:
            val = int(m)
            if abs(val) >= 100: return val
        except: continue
    return None

def _stitch_lines(lines: List[str]) -> List[str]:
    stitched = []
    skip_next = False
    start_info_re = re.compile(r'^([-+]\\d|ML|Over|Under|o\\s*\\d|u\\s*\\d|[-+]\\d{3})', re.I)
    
    for i in range(len(lines)):
        if skip_next:
            skip_next = False
            continue
        current = lines[i]
        if i < len(lines) - 1:
            next_line = lines[i+1]
            if not start_info_re.match(current) and start_info_re.match(next_line):
                stitched.append(f"{current} {next_line}")
                skip_next = True
                continue
        stitched.append(current)
    return stitched

def parse_with_regex(raw: RawPick) -> List[ParsedPick]:
    if not raw.raw_text: return []
    clean_text = raw.raw_text
    lines = [l.strip() for l in clean_text.split('\\n') if l.strip()]
    lines = [l for l in lines if len(l) < 150 and not l.lower().startswith('http')]
    lines = _stitch_lines(lines)
    
    results = []
    current_league = "Unknown"

    for line in lines:
        header_match = RE_LEAGUE_HEADER.match(line)
        if header_match:
            raw_league = header_match.group(1) or line.replace("(", "").replace(")", "").replace(":", "")
            current_league = standardizer.standardize_league(raw_league)
            continue

        clean_line = _clean_hype_text(line)
        
        for pat in PATTERNS:
            match = pat['re'].match(clean_line)
            if match:
                data = match.groupdict()
                odds_part = data.get('odds_part', '')
                
                if pat['type'] == 'Spread':
                    raw_spread = data['spread']
                    if raw_spread.lower() in ['pk', "pick'em", 'ev']:
                        final_spread = '-0'
                    else:
                        try:
                            val = float(raw_spread)
                            if abs(val) >= 100:
                                results.append(ParsedPick(
                                    raw_pick_id=raw.id or 0,
                                    league=current_league,
                                    bet_type="Moneyline",
                                    pick_value=f"{data['team'].strip()} ML",
                                    unit=_extract_unit(line),
                                    odds_american=int(val)
                                ))
                                break
                            final_spread = raw_spread
                        except: continue

                    results.append(ParsedPick(
                        raw_pick_id=raw.id or 0,
                        league=current_league,
                        bet_type="Spread",
                        pick_value=f"{data['team'].strip()} {final_spread}",
                        unit=_extract_unit(line),
                        odds_american=_extract_odds(line)
                    ))
                    break

                if pat['type'] == 'Total':
                    direction = data['dir'].lower()
                    if direction.startswith('o'): data['dir'] = 'Over'
                    elif direction.startswith('u'): data['dir'] = 'Under'
                
                if pat['type'] == 'Player Prop':
                    direction = data['dir'].lower()
                    if direction.startswith('o'): data['dir'] = 'Over'
                    elif direction.startswith('u'): data['dir'] = 'Under'
                    if not data.get('stat'): data['stat'] = ''

                pick_val = pat['val_fmt'].format(**data).strip()
                
                results.append(ParsedPick(
                    raw_pick_id=raw.id or 0,
                    league=current_league,
                    bet_type=pat['type'],
                    pick_value=pick_val,
                    unit=_extract_unit(line),
                    odds_american=_extract_odds(line)
                ))
                break
        
    return results
"""

# ==============================================================================
# 6. AI_PARSER.PY (Fixes: Strict JSON Prompt)
# ==============================================================================
AI_PARSER_PY = """import logging
import json
import re
from typing import List
import openai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import OPENROUTER_API_KEY, AI_PARSER_MODEL
from models import ParsedPick, RawPick

logger = logging.getLogger(__name__)

client = None
if OPENROUTER_API_KEY:
    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1", 
        api_key=OPENROUTER_API_KEY,
        default_headers={"HTTP-Referer": "http://localhost:3000"},
        max_retries=0
    )

PROMPT_TEMPLATE = \"\"\"
You are a specialized sports betting data extraction API.
You will be given unstructured Telegram messages containing betting picks.
Your ONLY task is to extract the picks into a valid JSON array.

### INPUT DATA
{data_json}

### RULES
1. **Output ONLY JSON**. Do not write "Here is the JSON" or markdown ticks. Just the array.
2. **IGNORE HYPE**: Ignore words like "Whale", "Lock", "Banger", "Max Bet".
3. **EXTRACT LINES**: Look for Team Names followed by spreads (-5, +3.5), Moneyline (ML), or Totals (Over/Under).
4. **MANDATORY**: You MUST include the "raw_pick_id" from the input in your output object.
5. **NULLS**: If unit or odds are not found, set them to null.
6. **NO PICKS?**: If the text contains no valid picks, return an empty array [].

### OUTPUT FORMAT
[
  {{"raw_pick_id": 123, "pick_value": "Lakers -5", "bet_type": "Spread", "unit": 2.0, "odds_american": -110, "league": "NBA"}}
]
\"\"\"

def _repair_json(text: str) -> str:
    # Remove markdown code blocks
    text = re.sub(r'```json', '', text, flags=re.I)
    text = re.sub(r'```', '', text)
    text = text.strip()
    
    # Attempt to find the array brackets
    start = text.find('[')
    end = text.rfind(']')
    
    if start != -1 and end != -1:
        return text[start:end+1]
    return "[]"

def parse_with_ai(raw_picks: List[RawPick]) -> List[ParsedPick]:
    if not client or not raw_picks: return []

    print(f"🤖 AI PARSER: Using Model -> {AI_PARSER_MODEL}")

    input_data = []
    for p in raw_picks:
        input_data.append({"raw_pick_id": p.id, "text": p.raw_text[:1000]})
    
    try:
        completion = client.chat.completions.create(
            model=AI_PARSER_MODEL,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(data_json=json.dumps(input_data))}],
            temperature=0.0
        )
        
        content = completion.choices[0].message.content
        clean_json = _repair_json(content)
        
        try:
            parsed_data = json.loads(clean_json)
        except json.JSONDecodeError:
            # Fallback: regex search for objects if array parsing fails
            objects = re.findall(r'\\{[^{}]+\\}', clean_json)
            parsed_data = [json.loads(o) for o in objects]

        results = []
        for item in parsed_data:
            # Safety: Ensure ID linkage
            if 'raw_pick_id' not in item and len(raw_picks) == 1:
                item['raw_pick_id'] = raw_picks[0].id

            if 'raw_pick_id' in item:
                try:
                    if item.get('league') is None: item['league'] = "Unknown"
                    if item.get('pick_value') is None: continue
                    # Sanity check length to filter hallucinations
                    if 3 < len(str(item['pick_value'])) < 50:
                        results.append(ParsedPick(**item))
                except Exception:
                    pass
        
        return results

    except Exception as e:
        logger.error(f"AI Error: {e}")
        # Don't raise, just return empty so flow continues (main loop handles retry logic)
        return []
"""

def main():
    print("🚀 APPLYING ALL SYSTEM FIXES...")
    
    with open("scrapers.py", "w", encoding="utf-8") as f:
        f.write(SCRAPERS_PY)
    print("✅ scrapers.py updated.")

    with open("database.py", "w", encoding="utf-8") as f:
        f.write(DATABASE_PY)
    print("✅ database.py updated.")

    with open("processing_service.py", "w", encoding="utf-8") as f:
        f.write(PROCESSING_SERVICE_PY)
    print("✅ processing_service.py updated.")

    with open("main.py", "w", encoding="utf-8") as f:
        f.write(MAIN_PY)
    print("✅ main.py updated.")

    with open("simple_parser.py", "w", encoding="utf-8") as f:
        f.write(SIMPLE_PARSER_PY)
    print("✅ simple_parser.py updated.")

    with open("ai_parser.py", "w", encoding="utf-8") as f:
        f.write(AI_PARSER_PY)
    print("✅ ai_parser.py updated.")

    print("\n✨ ALL PATCHES APPLIED.")
    print("\n👉 REQUIRED ACTION:")
    print("   Run this SQL in Supabase Editor to clear old bad data:")
    print("   DELETE FROM live_raw_picks WHERE status = 'pending';")
    print("\n   Then run 'python main.py'")

if __name__ == "__main__":
    main()