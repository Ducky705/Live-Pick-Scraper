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


def preprocess_image_v2(img):
    """
    IMPROVED image preprocessing for OCR.
    Enhancements over v1:
    - Lanczos4 upscaling (sharper than Cubic)
    - Gamma correction for contrast
    - Bilateral filter (preserves edges better)
    - Padding to help Tesseract with edge text
    """
    import cv2
    import numpy as np
    from PIL import Image
    
    # Convert PIL to OpenCV format
    if img.mode != 'RGB':
        img = img.convert('RGB')
    cv_img = np.array(img)
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
    
    # 1. UPSCALE using Lanczos4 (higher quality than Cubic)
    # Target: minimum 1600px width for better OCR
    min_width = 1600
    if cv_img.shape[1] < min_width:
        scale = min_width / cv_img.shape[1]
        cv_img = cv2.resize(cv_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    
    # 2. Add PADDING (50px white border) - helps Tesseract with edge text
    pad = 50
    cv_img = cv2.copyMakeBorder(cv_img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    
    # 3. Convert to Grayscale
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    
    # 4. GAMMA CORRECTION - enhance contrast for dark backgrounds
    # Gamma < 1 brightens, Gamma > 1 darkens
    gamma = 1.2  # Slightly darken to increase contrast
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(256)]).astype("uint8")
    gray = cv2.LUT(gray, table)
    
    # 5. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    # 6. BILATERAL FILTER - removes noise while preserving edges
    # Better than median blur for text
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # 7. ADAPTIVE THRESHOLDING (Otsu's method)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 8. Invert if background is dark
    white_ratio = np.sum(binary == 255) / binary.size
    if white_ratio < 0.3:
        binary = cv2.bitwise_not(binary)
    
    # 9. Morphological cleanup
    kernel = np.ones((1, 1), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    # Convert back to PIL
    return Image.fromarray(binary)


def deskew_image(gray):
    """
    Detect and correct image rotation/skew.
    Uses minAreaRect on contours to find the dominant angle.
    """
    import cv2
    import numpy as np
    
    # Find all contours
    coords = np.column_stack(np.where(gray > 0))
    if len(coords) < 10:
        return gray  # Not enough points to deskew
    
    # Get the minimum area rectangle
    angle = cv2.minAreaRect(coords)[-1]
    
    # Adjust angle
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    # Only rotate if angle is significant (> 0.5 degrees)
    if abs(angle) < 0.5:
        return gray
    
    # Rotate the image
    (h, w) = gray.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return rotated


def preprocess_image_v3(img, use_deskew=False, use_sharpen=True, use_nlm_denoise=True, remove_watermark=True):
    """
    BEST preprocessing pipeline with:
    - Red watermark removal (@cappersfree)
    - Unsharp Masking (sharpen edges)
    - Non-Local Means Denoising (better noise removal)
    - Deskewing DISABLED by default (images are always straight)
    
    Plus all v2 improvements (Lanczos4, padding, gamma, CLAHE).
    """
    import cv2
    import numpy as np
    from PIL import Image
    
    # Convert PIL to OpenCV format
    if img.mode != 'RGB':
        img = img.convert('RGB')
    cv_img = np.array(img)
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
    
    # 0. REMOVE RED WATERMARK (@cappersfree) - do this FIRST before any processing
    if remove_watermark:
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
        
        # Red spans across hue 0 and 180 in HSV, need two masks
        # Target: RGB(233, 9, 3) which is pure red
        # HSV red is around hue 0-10 and 170-180
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)
        
        # Dilate mask slightly to catch edges
        kernel = np.ones((3, 3), np.uint8)
        red_mask = cv2.dilate(red_mask, kernel, iterations=1)
        
        # Replace red pixels with white (or could use inpainting)
        cv_img[red_mask > 0] = [255, 255, 255]
    
    # 1. UPSCALE using Lanczos4
    min_width = 1600
    if cv_img.shape[1] < min_width:
        scale = min_width / cv_img.shape[1]
        cv_img = cv2.resize(cv_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    
    # 2. Add PADDING
    pad = 50
    cv_img = cv2.copyMakeBorder(cv_img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    
    # 3. Convert to Grayscale
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    
    # 4. SHARPENING (Unsharp Mask) - before other processing
    if use_sharpen:
        blurred = cv2.GaussianBlur(gray, (0, 0), 3)
        gray = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)
    
    # 5. GAMMA CORRECTION
    gamma = 1.2
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(256)]).astype("uint8")
    gray = cv2.LUT(gray, table)
    
    # 6. CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    # 7. DENOISING - Non-Local Means (better but slower) or Bilateral
    if use_nlm_denoise:
        gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
    else:
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # 8. DESKEW - correct rotation
    if use_deskew:
        gray = deskew_image(gray)
    
    # 9. ADAPTIVE THRESHOLDING (Otsu's method)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 10. Invert if background is dark
    white_ratio = np.sum(binary == 255) / binary.size
    if white_ratio < 0.3:
        binary = cv2.bitwise_not(binary)
    
    # 11. Morphological cleanup
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
        # NOTE: TESSDATA_PREFIX env var is set at module load time
        custom_config = '--psm 6 --oem 3'
        
        text = pytesseract.image_to_string(img, config=custom_config)
        return text.strip()
        
    except Exception as e:
        return f"[OCR Error: {str(e)}]"


def extract_text_v2(image_path):
    """
    IMPROVED text extraction with:
    - v2 preprocessing (Lanczos4, gamma, bilateral, padding)
    - Fallback PSM modes for different image layouts
    
    Args:
        image_path: Can be relative (from BASE_DIR) or absolute path
    """
    # Handle both relative and absolute paths
    if os.path.isabs(image_path):
        sys_path = image_path
    else:
        clean_path = image_path.lstrip('/').replace('/', os.sep)
        sys_path = os.path.join(BASE_DIR, clean_path)
    
    if not os.path.exists(sys_path):
        return f"[Error: Image not found at {sys_path}]"
    
    try:
        img = Image.open(sys_path)
        
        # Use improved preprocessing
        processed_img = preprocess_image_v2(img)
        
        # Try multiple PSM modes, return best result
        psm_modes = [
            ('--psm 6 --oem 3', 'uniform block'),      # Default
            ('--psm 3 --oem 3', 'auto segmentation'),  # Fully automatic
            ('--psm 11 --oem 3', 'sparse text'),       # Scattered text
        ]
        
        best_text = ""
        for config, desc in psm_modes:
            text = pytesseract.image_to_string(processed_img, config=config).strip()
            
            # Use longest result (more text = better for sports picks)
            if len(text) > len(best_text):
                best_text = text
            
            # If we got substantial text, don't try other modes
            if len(text) > 50:
                break
        
        return best_text
        
    except Exception as e:
        return f"[OCR Error: {str(e)}]"

