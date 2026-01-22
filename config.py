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

# App settings
# Changed to local folder since 'static' was removed
TEMP_IMG_DIR = os.path.join(BASE_DIR, 'temp_images')
if not os.path.exists(TEMP_IMG_DIR):
    os.makedirs(TEMP_IMG_DIR)

SESSION_FILE_PATH = os.path.join(EXEC_DIR, 'twitter_session.json') 
