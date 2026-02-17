# config.py
import os
import platform
import sys

# --- PATH HANDLING FOR FROZEN APP vs PYTHON SCRIPT ---
if getattr(sys, "frozen", False):
    # Running as compiled EXE/APP
    BASE_DIR = sys._MEIPASS
    # Directory where the executable lives (for saving sessions/logs)
    if platform.system() == "Darwin":
        # On Mac, sys.executable points inside the .app bundle.
        # We want the folder containing the .app
        EXEC_DIR = os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))
    else:
        EXEC_DIR = os.path.dirname(sys.executable)
else:
    # Running as Python script
    # Go up one level from 'src' to get project root
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    EXEC_DIR = BASE_DIR

# --- DIRECTORY STRUCTURE ---
DATA_DIR = os.path.join(EXEC_DIR, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

LOG_DIR = os.path.join(DATA_DIR, "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

OUTPUT_DIR = os.path.join(DATA_DIR, "output")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

TEMP_IMG_DIR = os.path.join(DATA_DIR, "temp_images")
if not os.path.exists(TEMP_IMG_DIR):
    os.makedirs(TEMP_IMG_DIR)

CACHE_DIR = os.path.join(DATA_DIR, "cache")
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")
if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)

DEBUG_REPORTS_DIR = os.path.join(DATA_DIR, "debug_reports")
if not os.path.exists(DEBUG_REPORTS_DIR):
    os.makedirs(DEBUG_REPORTS_DIR)

# App settings
SESSION_FILE_PATH = os.path.join(SESSIONS_DIR, "user_session")

# Load env vars
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TARGET_TELEGRAM_CHANNEL_ID = os.getenv("TARGET_TELEGRAM_CHANNEL_ID")
TARGET_DISCORD_CHANNEL_ID = os.getenv("TARGET_DISCORD_CHANNEL_ID")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_ID = os.getenv("TELEGRAM_API_ID") or os.getenv("API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH") or os.getenv("API_HASH")

# OPTIONAL: Proxy configuration
# Format: http://user:pass@host:port or http://host:port
PROXY_URL = os.getenv("PROXY_URL")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Anti-Detect User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]
