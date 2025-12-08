# src/ocr_handler.py
import pytesseract
from PIL import Image
import os
import sys
import stat

# --- CONFIGURATION ---
if getattr(sys, 'frozen', False):
    # Running as compiled APP
    BASE_DIR = sys._MEIPASS
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TESSDATA_DIR = os.path.join(BASE_DIR, 'tessdata')

# --- OS SPECIFIC PATHS ---
if sys.platform == 'win32':
    TESSERACT_BIN = os.path.join(BASE_DIR, 'bin', 'win', 'tesseract.exe')
else:
    # Mac / Linux
    TESSERACT_BIN = os.path.join(BASE_DIR, 'bin', 'mac', 'tesseract')

# --- CRITICAL MAC SETUP ---
# To make Tesseract portable, we must tell it where to find the bundled .dylib files.
# We do this by setting the DYLD_LIBRARY_PATH environment variable for the process.
if sys.platform == 'darwin':
    mac_bin_folder = os.path.dirname(TESSERACT_BIN)
    
    # 1. Update Environment Variable
    # This tells the dynamic linker: "Look in bin/mac for shared libraries"
    current_path = os.environ.get('DYLD_LIBRARY_PATH', '')
    os.environ['DYLD_LIBRARY_PATH'] = f"{mac_bin_folder}:{current_path}"
    
    # 2. Ensure Executable Permissions
    # PyInstaller sometimes strips execution rights from bundled binaries.
    if os.path.exists(mac_bin_folder):
        for filename in os.listdir(mac_bin_folder):
            filepath = os.path.join(mac_bin_folder, filename)
            try:
                st = os.stat(filepath)
                os.chmod(filepath, st.st_mode | stat.S_IEXEC)
            except Exception:
                pass

# Set Tesseract Data Path Env Var
os.environ['TESSDATA_PREFIX'] = TESSDATA_DIR

# Configure Pytesseract Command
if os.path.exists(TESSERACT_BIN):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_BIN
else:
    # Fallback for dev environment if bin folder isn't populated
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

def extract_text(image_relative_path):
    # Handle path differences between dev and frozen app
    # image_relative_path comes in like "/static/temp_images/..."
    clean_path = image_relative_path.lstrip('/').replace('/', os.sep)
    
    sys_path = os.path.join(BASE_DIR, clean_path)
    
    if not os.path.exists(sys_path):
        return f"[Error: Image not found at {sys_path}]"
    
    try:
        img = Image.open(sys_path)
        
        # Explicitly pass tessdata dir config as a safety net
        custom_config = f'--tessdata-dir "{TESSDATA_DIR}"'
        
        text = pytesseract.image_to_string(img, config=custom_config)
        return text.strip()
    except Exception as e:
        return f"[OCR Error: {str(e)}]"
