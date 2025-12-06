import os

# ==========================================
# 1. STRICT CONFIG.PY
# ==========================================
CONFIG_PY = """import os
import logging
from typing import List, Set, Union
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

load_dotenv()

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

EASTERN_TIMEZONE = ZoneInfo('US/Eastern')
UTC_TIMEZONE = ZoneInfo('UTC')

OPERATIONAL_START_HOUR_ET = int(os.getenv('OPERATIONAL_START_HOUR_ET', '11'))
OPERATIONAL_END_HOUR_ET = int(os.getenv('OPERATIONAL_END_HOUR_ET', '23'))
SCRAPE_WINDOW_HOURS = int(os.getenv('SCRAPE_WINDOW_HOURS', '48'))
ARCHIVE_AFTER_HOURS = int(os.getenv('ARCHIVE_PENDING_PICKS_AFTER_HOURS', '72'))

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_SESSION_NAME = os.getenv('TELEGRAM_SESSION_NAME')

def parse_int_list(env_var: str) -> Set[int]:
    if not env_var: return set()
    clean = env_var.replace('[', '').replace(']', '').replace('"', '').replace("'", "")
    return {int(x.strip()) for x in clean.split(',') if x.strip().lstrip('-').isdigit()}

def parse_telegram_identifiers(env_var: str) -> List[Union[str, int]]:
    if not env_var: return []
    items = []
    clean = env_var.replace('[', '').replace(']', '').replace('"', '').replace("'", "")
    for x in clean.split(','):
        x = x.strip()
        if not x: continue
        if x.lstrip('-').isdigit():
            items.append(int(x))
        else:
            items.append(x)
    return items

TELEGRAM_CHANNELS = parse_telegram_identifiers(os.getenv('TELEGRAM_CHANNEL_URLS', ''))
AGGREGATOR_CHANNEL_IDS = parse_int_list(os.getenv('AGGREGATOR_CHANNEL_IDS', ''))

DISTRIBUTION_CHANNEL_ID = os.getenv('DISTRIBUTION_CHANNEL_ID')
if DISTRIBUTION_CHANNEL_ID and DISTRIBUTION_CHANNEL_ID.lstrip('-').isdigit():
    DISTRIBUTION_CHANNEL_ID = int(DISTRIBUTION_CHANNEL_ID)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# --- STRICT MODEL LOADING ---
# This ensures NO default value exists. 
# If the .env or Secret is missing, this will be None.
AI_PARSER_MODEL = os.getenv("AI_PARSER_MODEL")

if not AI_PARSER_MODEL:
    logging.warning("⚠️ AI_PARSER_MODEL is not set! The scraper will fail if it tries to use AI.")

# --- BLACKLIST ---
BLACKLISTED_CAPPERS = {
    'free cappers picks', 'the capper', 'capper picks', 'free picks', 
    'daily picks', 'best bets', 'pick central', 'bet tips', 'sports picks', 
    'winners only', 'pro picks', 'capper network', 'betting tips',
    'cappers free', 'cappersfree', 'dm', 'bonus', 'promo'
}

HYPE_TERMS = {
    'max bet', 'whale play', 'lock of the day', 'guaranteed', 'bomb', 
    'nuke', 'system play', 'vip pick', 'free pick', 'bonus', 'promo',
    'hammer', 'stake', 'unit', 'play of the day', 'potd', 'bankroll',
    'investment', 'insider'
}

LEAGUE_STANDARDS = {
    'NFL': 'NFL', 'NCAAF': 'NCAAF', 'NBA': 'NBA', 'NCAAB': 'NCAAB',
    'WNBA': 'WNBA', 'MLB': 'MLB', 'NHL': 'NHL', 'EPL': 'EPL',
    'MLS': 'MLS', 'UCL': 'UCL', 'UFC': 'UFC', 'PFL': 'PFL',
    'TENNIS': 'TENNIS', 'PGA': 'PGA', 'F1': 'F1', 'OTHER': 'Other'
}

LEAGUE_MAP = {
    'NATIONAL FOOTBALL LEAGUE': 'NFL', 'COLLEGE FOOTBALL': 'NCAAF',
    'NATIONAL BASKETBALL ASSOCIATION': 'NBA', 'COLLEGE BASKETBALL': 'NCAAB',
    'MAJOR LEAGUE BASEBALL': 'MLB', 'NATIONAL HOCKEY LEAGUE': 'NHL',
    'PREMIER LEAGUE': 'EPL', 'SOCCER': 'EPL', 'CHAMPIONS LEAGUE': 'UCL',
    'MMA': 'UFC', 'GOLF': 'PGA', 'FORMULA 1': 'F1'
}
LEAGUE_MAP.update(LEAGUE_STANDARDS)

BET_TYPE_MAP = {
    'MONEYLINE': 'Moneyline', 'ML': 'Moneyline',
    'SPREAD': 'Spread', 'RUN LINE': 'Spread', 'PUCK LINE': 'Spread',
    'TOTAL': 'Total', 'OVER/UNDER': 'Total',
    'PLAYER PROP': 'Player Prop', 'PROP': 'Player Prop',
    'TEAM PROP': 'Team Prop', 'TTU': 'Team Prop', 'TTO': 'Team Prop',
    'PARLAY': 'Parlay', 'TEASER': 'Teaser'
}
"""

# ==========================================
# 2. VERBOSE AI_PARSER.PY
# ==========================================
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
You are a sports betting data extractor. 
Your job is to find valid picks hidden in messy Telegram messages and OCR text.

### RULES
1. **IGNORE HYPE**: Words like "Banger", "Whale", "Lock" are noise.
2. **FIND THE LINES**: Look for Team Names followed by a spread (+5, -3.5) or Moneyline.
3. **OCR IS MESSY**: "Cow boy +5" -> "Cowboys +5".
4. **IMPORTANT**: You MUST include the "raw_pick_id" from the input in your output object.

### EXAMPLES
Input: {{"raw_pick_id": 123, "text": "Lakers -5"}}
Output: [{{"raw_pick_id": 123, "pick_value": "Lakers -5", "bet_type": "Spread", "unit": null, "odds_american": null, "league": "NBA"}}]

### DATA TO PROCESS
{data_json}
\"\"\"

def _repair_json(text: str) -> str:
    text = re.sub(r'```json', '', text, flags=re.I)
    text = re.sub(r'```', '', text)
    text = text.strip()
    end = text.rfind(']')
    if end == -1: return "[]"
    starts = [m.start() for m in re.finditer(r'\[', text)]
    for start in reversed(starts):
        if start >= end: continue
        candidate = text[start:end+1]
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            continue
    return "[]"

def parse_with_ai(raw_picks: List[RawPick]) -> List[ParsedPick]:
    if not client or not raw_picks: return []

    # --- DEBUG: PRINT MODEL BEING USED ---
    print(f"🤖 AI PARSER: Using Model -> {AI_PARSER_MODEL}")
    # -------------------------------------

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
            objects = re.findall(r'\{[^{}]+\}', clean_json)
            parsed_data = [json.loads(o) for o in objects]

        results = []
        for item in parsed_data:
            if 'raw_pick_id' not in item and len(raw_picks) == 1:
                item['raw_pick_id'] = raw_picks[0].id

            if 'raw_pick_id' in item:
                try:
                    if item.get('league') is None: item['league'] = "Unknown"
                    if item.get('pick_value') is None: continue
                    if len(item['pick_value']) > 3:
                        results.append(ParsedPick(**item))
                except Exception as e:
                    pass
        
        return results

    except Exception as e:
        logger.error(f"AI Error: {e}")
        raise
"""

# ==========================================
# 3. TIMEOUT-SAFE MAIN.PY
# ==========================================
MAIN_PY = """import asyncio
import logging
import argparse
import sys
from datetime import datetime

import config
from scrapers import run_scrapers
from processing_service import process_picks
from database import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_pipeline(force=False):
    logger.info("🚀 STARTING SNIPER PIPELINE")
    
    # --- PHASE 1: SCRAPE TODAY'S PICKS ---
    try:
        logger.info("📡 Checking Telegram for TODAY'S messages...")
        await run_scrapers()
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
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_pipeline(force=args.force))
"""

def write_file(filename, content):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Updated {filename}")

if __name__ == "__main__":
    write_file('config.py', CONFIG_PY)
    write_file('ai_parser.py', AI_PARSER_PY)
    write_file('main.py', MAIN_PY)
    
    print("\n👉 ACTION REQUIRED: Check your GitHub Repository Secrets.")
    print("   Ensure 'AI_PARSER_MODEL' is set to 'deepseek/deepseek-chat' (or your preferred model).")
    print("   The batch limit in main.py has been reduced to 2 to prevent timeouts.")