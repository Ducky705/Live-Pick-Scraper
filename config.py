# config.py
import os
import sys
import platform

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

# --- CREDENTIALS ---
API_ID = '24208869'
API_HASH = '3933396224fdfa39215a499c65db0466'
SUPABASE_URL = 'https://igrhzymvzndnjkrhhhxe.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imlncmh6eW12em5kbmprcmhoaHhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTM0NTg2OSwiZXhwIjoyMDc0OTIxODY5fQ.JgOjphAc0u5aSuKT4o_c51gzUvxH8TwOVaRhg0XTSdQ' 

# --- OS-SPECIFIC BINARY PATHS ---
# We expect a folder structure:
# /bin
#   /win -> contains tesseract.exe and dlls
#   /mac -> contains tesseract binary and dylibs
# /tessdata -> contains eng.traineddata

if platform.system() == 'Windows':
    TESSERACT_BIN = os.path.join(BASE_DIR, 'bin', 'win', 'tesseract.exe')
elif platform.system() == 'Darwin':
    TESSERACT_BIN = os.path.join(BASE_DIR, 'bin', 'mac', 'tesseract')
else:
    # Linux or other
    TESSERACT_BIN = 'tesseract'

# Common Data Path
TESSDATA_DIR = os.path.join(BASE_DIR, 'tessdata')

# App settings
TEMP_IMG_DIR = os.path.join(BASE_DIR, 'static', 'temp_images')
if not os.path.exists(TEMP_IMG_DIR):
    os.makedirs(TEMP_IMG_DIR)

SESSION_FILE_PATH = os.path.join(EXEC_DIR, 'user_session')

# --- AUTO-UPDATE CONFIGURATION ---
APP_VERSION = "2.0.1"
GITHUB_REPO = "Ducky705/Telegram-Scraper"  # Format: "owner/repo"
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')  # Set in .env file
