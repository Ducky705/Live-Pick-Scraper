import os
import sys
import platform
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv()

# --- PATH HANDLING FOR FROZEN APP vs PYTHON SCRIPT ---
if getattr(sys, 'frozen', False):
    # Running as compiled EXE/APP
    BASE_DIR = sys._MEIPASS
    # Directory where the executable lives (for saving sessions/logs)
    if platform.system() == 'Darwin':
        # On Mac, sys.executable points inside the .app bundle. 
        # We want the folder containing the .app
        EXEC_DIR = os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))
    else:
        EXEC_DIR = os.path.dirname(sys.executable)
else:
    # Running as Python script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXEC_DIR = BASE_DIR

# App settings
# Changed to local folder since 'static' was removed
TEMP_IMG_DIR = os.path.join(BASE_DIR, 'temp_images')
if not os.path.exists(TEMP_IMG_DIR):
    os.makedirs(TEMP_IMG_DIR)

SESSION_FILE_PATH = os.path.join(EXEC_DIR, 'twitter_session.json') 

# Environment Variables
TARGET_TELEGRAM_CHANNEL_ID = os.getenv('TARGET_TELEGRAM_CHANNEL_ID')
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
