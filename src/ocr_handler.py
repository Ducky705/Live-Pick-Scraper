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
# First check local tessdata, then fallback to Homebrew's tessdata
if os.path.exists(TESSDATA_DIR):
    os.environ['TESSDATA_PREFIX'] = TESSDATA_DIR
elif os.path.exists('/opt/homebrew/share/tessdata'):
    # Homebrew on Apple Silicon
    TESSDATA_DIR = '/opt/homebrew/share/tessdata'
    os.environ['TESSDATA_PREFIX'] = TESSDATA_DIR
elif os.path.exists('/usr/local/share/tessdata'):
    # Homebrew on Intel Mac
    TESSDATA_DIR = '/usr/local/share/tessdata'
    os.environ['TESSDATA_PREFIX'] = TESSDATA_DIR

# Configure Pytesseract Command
if os.path.exists(TESSERACT_BIN):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_BIN
else:
    # Fallback for dev environment - use system tesseract
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

def preprocess_image(img):
    """
    Advanced image preprocessing for OCR using OpenCV.
    Optimized for sports betting images with:
    - Dark backgrounds, light text
    - Gradients and watermarks
    - Stylized fonts
    """
    import cv2
    import numpy as np
    from PIL import Image
    
    # Convert PIL to OpenCV format
    if img.mode != 'RGB':
        img = img.convert('RGB')
    cv_img = np.array(img)
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
    
    # 1. UPSCALE if too small (OCR needs ~300 DPI equivalent)
    min_width = 1200
    if cv_img.shape[1] < min_width:
        scale = min_width / cv_img.shape[1]
        cv_img = cv2.resize(cv_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    # 2. Convert to Grayscale
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    
    # 3. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    # Much better than simple contrast for uneven lighting
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    # 4. DENOISE using median filter (removes salt-and-pepper noise)
    gray = cv2.medianBlur(gray, 3)
    
    # 5. ADAPTIVE THRESHOLDING (Otsu's method)
    # Better than global threshold for images with shadows/gradients
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 6. Optional: Invert if background is dark (more white pixels = light bg)
    # Sports betting images often have dark backgrounds
    white_ratio = np.sum(binary == 255) / binary.size
    if white_ratio < 0.3:  # Mostly dark, invert
        binary = cv2.bitwise_not(binary)
    
    # 7. Slight morphological cleanup (remove tiny noise)
    kernel = np.ones((1, 1), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    # Convert back to PIL
    return Image.fromarray(binary)

def extract_text(image_relative_path):
    """
    Extract text from image using Tesseract OCR with advanced preprocessing.
    Uses character whitelisting for sports betting data.
    """
    # Handle path differences between dev and frozen app
    clean_path = image_relative_path.lstrip('/').replace('/', os.sep)
    sys_path = os.path.join(BASE_DIR, clean_path)
    
    if not os.path.exists(sys_path):
        return f"[Error: Image not found at {sys_path}]"
    
    try:
        img = Image.open(sys_path)
        
        # Advanced preprocessing
        img = preprocess_image(img)
        
        # Tesseract config optimized for sports betting text:
        # PSM 6 = Assume uniform block of text
        # OEM 3 = Default OCR Engine Mode
        # Whitelist: Letters, numbers, common sports betting symbols
        whitelist = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-.,/:()@#$%& "
        
        custom_config = (
            f'--tessdata-dir "{TESSDATA_DIR}" '
            f'--psm 6 --oem 3 '
            f'-c tessedit_char_whitelist="{whitelist}"'
        )
        
        text = pytesseract.image_to_string(img, config=custom_config)
        return text.strip()
        
    except Exception as e:
        return f"[OCR Error: {str(e)}]"
