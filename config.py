# File: ./config.py
import os
import logging
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

# --- Environment Loading ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Timezone Configuration ---
EASTERN_TIMEZONE = ZoneInfo('US/Eastern')
UTC_TIMEZONE = ZoneInfo('UTC')

# --- Pipeline Operational Hours (Eastern Time) ---
OPERATIONAL_START_HOUR_ET = int(os.getenv('OPERATIONAL_START_HOUR_ET', '11'))
OPERATIONAL_END_HOUR_ET = int(os.getenv('OPERATIONAL_END_HOUR_ET', '23'))

# --- Supabase Configuration ---
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# --- Telegram Configuration ---
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_SESSION_NAME = os.getenv('TELEGRAM_SESSION_NAME')
raw_telegram_channels = [url.strip() for url in os.getenv('TELEGRAM_CHANNEL_URLS', '').split(',') if url.strip()]
TELEGRAM_CHANNELS = []
for channel in raw_telegram_channels:
    try:
        TELEGRAM_CHANNELS.append(int(channel))
    except ValueError:
        TELEGRAM_CHANNELS.append(channel)
SCRAPE_WINDOW_HOURS = int(os.getenv('SCRAPE_WINDOW_HOURS', '48'))

raw_aggregator_ids = [id.strip() for id in os.getenv('AGGREGATOR_CHANNEL_IDS', '').split(',') if id.strip()]
AGGREGATOR_CHANNEL_IDS = {int(id) for id in raw_aggregator_ids if id.lstrip('-').isdigit()}

# --- Channel Name Blacklist (Watermarks that are NOT actual cappers) ---
BLACKLISTED_CAPPER_NAMES = [
    'Free Cappers Picks',
    'Free Cappers Picks | 🔮',
    'FREE CAPPERS PICKS',
    'FREE CAPPERS PICKS | 🔮',
    'The Capper',
    'Capper Picks',
    'Free Picks',
    'Daily Picks',
    'Best Bets',
    'Pick Central',
    'Bet Tips',
    'Sports Picks',
    'Winners Only',
    'Pro Picks',
    'Capper Network'
]


# --- AI Parser Configuration ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
AI_PARSER_MODEL = os.getenv("AI_PARSER_MODEL", "google/gemini-2.0-flash-exp:free")

# --- Maintenance Configuration ---
ARCHIVE_PENDING_PICKS_AFTER_HOURS = int(os.getenv('ARCHIVE_PENDING_PICKS_AFTER_HOURS', '72'))

# --- Data Standardization Constants ---
LEAGUE_STANDARDS = {
    'NATIONAL FOOTBALL LEAGUE': 'NFL', 'NFL': 'NFL',
    'NCAA FOOTBALL': 'NCAAF', 'COLLEGE FOOTBALL': 'NCAAF', 'NCAAF': 'NCAAF',
    'NATIONAL BASKETBALL ASSOCIATION': 'NBA', 'NBA': 'NBA',
    'NCAA BASKETBALL': 'NCAAB', 'COLLEGE BASKETBALL': 'NCAAB', 'NCAAB': 'NCAAB',
    'WOMENS NATIONAL BASKETBALL': 'WNBA', 'WNBA': 'WNBA',
    'MAJOR LEAGUE BASEBALL': 'MLB', 'MLB': 'MLB',
    'NATIONAL HOCKEY LEAGUE': 'NHL', 'NHL': 'NHL',
    'ENGLISH PREMIER LEAGUE': 'EPL', 'PREMIER LEAGUE': 'EPL', 'EPL': 'EPL', 'SOCCER': 'EPL',
    'MAJOR LEAGUE SOCCER': 'MLS', 'MLS': 'MLS',
    'UEFA CHAMPIONS LEAGUE': 'UCL', 'CHAMPIONS LEAGUE': 'UCL', 'UCL': 'UCL',
    'ULTIMATE FIGHTING CHAMPIONSHIP': 'UFC', 'MMA': 'UFC', 'UFC': 'UFC',
    'PROFESSIONAL FIGHTERS LEAGUE': 'PFL', 'PFL': 'PFL',
    'TENNIS': 'TENNIS', 'ATP': 'TENNIS', 'WTA': 'TENNIS',
    'PGA TOUR': 'PGA', 'GOLF': 'PGA', 'PGA': 'PGA',
    'FORMULA 1': 'F1', 'F1': 'F1',
    'OTHER': 'Other', 'PARLAY': 'Other', 'MULTI-LEAGUE': 'Other'
}

BET_TYPE_STANDARDS = {
    'MONEYLINE': 'Moneyline', 'ML': 'Moneyline',
    'SPREAD': 'Spread', 'POINT SPREAD': 'Spread', 'RUN LINE': 'Spread', 'PUCK LINE': 'Spread',
    'TOTAL': 'Total', 'OVER/UNDER': 'Total',
    'PLAYER PROP': 'Player Prop', 'PROP': 'Player Prop',
    # --- FIX: Added TTU and TTO to map to Team Prop ---
    'TEAM PROP': 'Team Prop', 'TEAM TOTAL': 'Team Prop', 'TTU': 'Team Prop', 'TTO': 'Team Prop',
    'GAME PROP': 'Game Prop',
    'PERIOD': 'Period', 'HALF': 'Period', 'QUARTER': 'Period', 'INNING': 'Period',
    'PARLAY': 'Parlay', 'ACCUMULATOR': 'Parlay',
    'TEASER': 'Teaser',
    'FUTURE': 'Future', 'CHAMPIONSHIP': 'Future',
    'UNKNOWN': 'Unknown', 'MISC': 'Unknown'
}

# --- Status Constants ---
PICK_STATUS_PENDING = 'pending'
PICK_STATUS_PROCESSED = 'processed'
PICK_STATUS_FAILED = 'failed'
PICK_STATUS_ARCHIVED = 'archived'