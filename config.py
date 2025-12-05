import os
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
