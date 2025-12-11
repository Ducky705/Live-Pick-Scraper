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

    async def scrape(self):
        if not self.client:
            logger.warning("Telegram Client not initialized. Skipping scrape.")
            return

        try:
            # Wrap connection logic in try/except to prevent crash on invalid session
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
                    
                    new_checkpoint = latest_msg_date if latest_msg_date else run_start_time
                    db.update_checkpoint(channel_id, new_checkpoint)
                        
                except Exception as e:
                    logger.error(f"Error scraping {entity_id}: {e}")
        finally:
            if self.client.is_connected():
                await self.client.disconnect()

async def run_scrapers():
    s = TelegramScraper()
    await s.scrape()
"""

SIMPLE_PARSER_PY = """import re
import logging
from typing import Optional, List
from models import ParsedPick, RawPick

logger = logging.getLogger(__name__)

# 1. Units: "5u", "5.5 units", "10 star"
RE_UNIT = re.compile(r'\\b(?P<val>\\d+(\\.\\d+)?)\\s*(u|unit|star)s?\\b', re.IGNORECASE)

# 2. Odds Extraction
# Looks for 3+ digit numbers with optional +/- (e.g., -110, +200, 110)
RE_ODDS = re.compile(r'(?<!\\d)([-+]?\\d{3,})(?!\\d)')

PATTERNS = [
    # 1. TOTALS (Start with O/U): "Over 215.5", "o 55.5"
    {
        'type': 'Total',
        're': re.compile(r"^(?P<dir>o|u|over|under)\\s*(?P<line>\\d+(\\.\\d+)?)\\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{dir} {line}"
    },
    # 2. PLAYER PROPS / TEAM TOTALS (Name + O/U + Line): "Jalen Hurts Over 31.5"
    {
        'type': 'Player Prop', 
        're': re.compile(r"^(?P<name>.+?)\\s+(?P<dir>over|under|o|u)\\s*(?P<line>\\d+(\\.\\d+)?)\\s*(?P<stat>[a-zA-Z\\s]+)?(?P<odds_part>.*)$", re.I),
        'val_fmt': "{name} {dir} {line} {stat}"
    },
    # 3. MONEYLINE (Explicit): "Lakers ML", "Celtics Moneyline"
    {
        'type': 'Moneyline',
        're': re.compile(r"^(?P<team>.+?)\\s+(?:ML|Moneyline|M/L)\\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{team} ML"
    },
    # 4. SPREADS / HANDICAPS (The tricky one)
    # Matches "Team -5", "Team +3.5", "Team -110" (Ambiguous)
    {
        'type': 'Spread',
        're': re.compile(r"^(?!over|under|o\\s|u\\s)(?P<team>.{2,}?)\\s+(?P<spread>[-+]\\d+(\\.\\d+)?|Pk|Pick'em|Ev)\\s*(?P<odds_part>.*)$", re.I),
        'val_fmt': "{team} {spread}"
    }
]

def _extract_unit(text: str) -> Optional[float]:
    if not text: return None
    m = RE_UNIT.search(text)
    if m:
        try: return float(m.group('val'))
        except: pass
    
    lower = text.lower()
    if 'max' in lower or 'whale' in lower: return 5.0
    if 'pod' in lower or 'potd' in lower: return 3.0
    return None

def _extract_odds(text: str) -> Optional[int]:
    if not text: return None
    # Look for odds in the remaining text
    matches = RE_ODDS.findall(text)
    for m in matches:
        try:
            val = int(m)
            # Standard US odds are usually >100 or <-100
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

def parse_with_regex(raw: RawPick) -> Optional[ParsedPick]:
    if not raw.raw_text: return None
    
    lines = [l.strip() for l in raw.raw_text.split('\\n') if l.strip()]
    lines = [l for l in lines if len(l) < 150 and not l.lower().startswith('http')]
    lines = _stitch_lines(lines)
    
    if len(lines) > 6: return None

    for line in lines:
        for pat in PATTERNS:
            match = pat['re'].match(line)
            if match:
                data = match.groupdict()
                odds_part = data.get('odds_part', '')
                
                # --- LOGIC TO HANDLE SPREAD VS ODDS ---
                if pat['type'] == 'Spread':
                    raw_spread = data['spread']
                    
                    # Handle "Pk", "Ev"
                    if raw_spread.lower() in ['pk', "pick'em", 'ev']:
                        final_spread = '-0'
                    else:
                        try:
                            val = float(raw_spread)
                            # CRITICAL CHECK: Is this a spread (-5) or Moneyline odds (-110)?
                            if abs(val) >= 100:
                                # It's actually Moneyline Odds!
                                # Example: "Lakers -150" -> Team: Lakers, Odds: -150
                                return ParsedPick(
                                    raw_pick_id=raw.id or 0,
                                    league="Unknown",
                                    bet_type="Moneyline",
                                    pick_value=f"{data['team'].strip()} ML",
                                    unit=_extract_unit(odds_part),
                                    odds_american=int(val)
                                )
                            final_spread = raw_spread
                        except:
                            continue # Not a valid number

                    # If we are here, it's a valid small number spread (e.g. -5)
                    # Now look for odds in the 'odds_part' (e.g. "+110" in "Lakers -5 +110")
                    found_odds = _extract_odds(odds_part)
                    
                    return ParsedPick(
                        raw_pick_id=raw.id or 0,
                        league="Unknown",
                        bet_type="Spread",
                        pick_value=f"{data['team'].strip()} {final_spread}",
                        unit=_extract_unit(odds_part),
                        odds_american=found_odds
                    )

                # --- HANDLING TOTALS & PROPS ---
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
                
                return ParsedPick(
                    raw_pick_id=raw.id or 0,
                    league="Unknown",
                    bet_type=pat['type'],
                    pick_value=pick_val,
                    unit=_extract_unit(odds_part),
                    odds_american=_extract_odds(odds_part)
                )
    return None
"""

SCHEDULER_PY = """import datetime
import os
import re

# ==============================================================================
# 🧠 THE BRAIN: SEASONAL LOGIC
# ==============================================================================
def get_optimized_schedule():
    today = datetime.date.today()
    month = today.month

    # ------------------------------------------------------------------
    # SEASON 1: THE "FULL SEND" (September - January)
    # Active: NFL, NCAAF, NBA, NHL, CBB
    # Strategy: Heavy Weekend Mornings (Football) + Heavy Daily Evenings
    # ------------------------------------------------------------------
    if month in [9, 10, 11, 12, 1]:
        print(f"📅 Month {month}: Detected FOOTBALL/WINTER Season. Loading Max Schedule.")
        return [
            "- cron: '0 14-23,0-4 * * *'",       # Baseline: Hourly 10am-12am ET
            "- cron: '15,30,45 21-23 * * 1-5'",  # Weekdays: Every 15m 5pm-8pm ET (NBA/NHL/MNF)
            "- cron: '15,30,45 15-20 * * 0,6'"   # Weekends: Every 15m 11am-4pm ET (NFL/NCAAF Kickoffs)
        ]

    # ------------------------------------------------------------------
    # SEASON 2: MARCH MADNESS (March)
    # Active: NCAA Tournament, NBA, NHL
    # Strategy: Heavy All Day on Weekends
    # ------------------------------------------------------------------
    elif month == 3:
        print(f"📅 Month {month}: Detected MARCH MADNESS. Loading Tournament Schedule.")
        return [
            "- cron: '0 14-23,0-4 * * *'",       # Baseline: Hourly
            "- cron: '15,30,45 16-23 * * 4-7'"   # Thu-Sun: Every 15m 12pm-7pm ET (Tournament Games)
        ]

    # ------------------------------------------------------------------
    # SEASON 3: PLAYOFFS & BASEBALL (February, April, May, June)
    # Active: NBA/NHL Playoffs, MLB
    # Strategy: Focus on Evenings. No Weekend Morning Blitz needed (No Football).
    # ------------------------------------------------------------------
    elif month in [2, 4, 5, 6]:
        print(f"📅 Month {month}: Detected SPRING/PLAYOFF Season. Loading Evening Schedule.")
        return [
            "- cron: '0 15-23,0-4 * * *'",       # Baseline: Hourly
            "- cron: '15,30,45 22-23 * * *'"     # Daily: Every 15m 6pm-8pm ET (Playoff Tipoffs/First Pitch)
        ]

    # ------------------------------------------------------------------
    # SEASON 4: THE DEAD ZONE (July - August)
    # Active: MLB Only
    # Strategy: Save Money. Hourly only. No 15-minute blitzes.
    # ------------------------------------------------------------------
    else:
        print(f"📅 Month {month}: Detected SUMMER/OFF-SEASON. Loading Economy Schedule.")
        return [
            "- cron: '0 16-23,0-4 * * *'"        # Baseline: Hourly 12pm-12am ET only
        ]

# ==============================================================================
# 📝 THE WRITER: YAML UPDATER
# ==============================================================================
def update_workflow_file():
    workflow_path = '.github/workflows/scrape_and_process.yml'
    
    if not os.path.exists(workflow_path):
        print("❌ Workflow file not found.")
        return

    with open(workflow_path, 'r', encoding='utf-8') as f:
        content = f.read()

    new_cron_lines = get_optimized_schedule()
    
    # Regex to find the existing schedule block and replace it
    # Looks for "schedule:" followed by any indented lines starting with "- cron:"
    pattern = r"(schedule:\\s*\\n)(\\s*- cron:.*\\n)+"
    
    # Construct the replacement string
    replacement = "\\\\1" + "\\n".join([f"    {line}" for line in new_cron_lines]) + "\\n"
    
    new_content = re.sub(pattern, replacement, content)

    if new_content != content:
        with open(workflow_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✅ Schedule updated successfully.")
        # Create a flag file so the GitHub Action knows to commit
        with open("schedule_updated.flag", "w") as f:
            f.write("true")
    else:
        print("⚡ Schedule is already optimized for this month. No changes.")

if __name__ == "__main__":
    update_workflow_file()
"""

SCHEDULE_MANAGER_YML = """name: Schedule Manager

on:
  # Run at 00:00 on the 1st and 15th of every month
  schedule:
    - cron: '0 0 1,15 * *'
  # Allow manual trigger to force an update
  workflow_dispatch:

permissions:
  contents: write

jobs:
  optimize-schedule:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Calculate Optimal Schedule
        run: python scheduler.py

      - name: Commit Changes
        run: |
          if [ -f schedule_updated.flag ]; then
            git config --global user.name 'SniperBot'
            git config --global user.email 'bot@noreply.github.com'
            git add .github/workflows/scrape_and_process.yml
            git commit -m "📅 SniperBot: Optimized schedule for new sports season"
            git push
            echo "🚀 Schedule updated and pushed to repo."
          else
            echo "💤 No schedule changes needed."
          fi
"""

# REMOVED CACHE TESSERACT STEP TO FIX PERMISSION ERROR
SCRAPE_AND_PROCESS_YML = """name: Sniper Pick Scraper

on:
  workflow_dispatch:
  push:
    branches: ["main"]
  
  # 🤖 DYNAMIC SCHEDULE BLOCK
  # This block is automatically managed by scheduler.py
  # Do not manually edit the cron lines below, they will be overwritten.
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
          python main.py --force
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
    print("🚀 Applying Smart System Fixes...")
    
    files_to_write = {
        "scrapers.py": SCRAPERS_PY,
        "simple_parser.py": SIMPLE_PARSER_PY,
        "scheduler.py": SCHEDULER_PY,
        ".github/workflows/schedule_manager.yml": SCHEDULE_MANAGER_YML,
        ".github/workflows/scrape_and_process.yml": SCRAPE_AND_PROCESS_YML
    }

    for path, content in files_to_write.items():
        write_file(path, content)

    print("\n🎉 All files updated successfully!")
    print("👉 Now run: git add . && git commit -m 'Apply Smart Schedule System' && git push")

if __name__ == "__main__":
    main()