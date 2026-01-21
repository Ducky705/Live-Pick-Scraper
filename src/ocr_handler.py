
# src/ocr_handler.py
import pytesseract
from PIL import Image
import os
import sys
import stat
import json
import re
import logging
import time
import base64
import io
from src.openrouter_client import openrouter_completion
from src.provider_pool import pooled_completion
from src.two_pass_verifier import TwoPassVerifier
from src.vision_one_shot import parse_image_direct
from src.image_classifier import ImageClassifier, OCRStrategy
from config import TEMP_IMG_DIR
from concurrent.futures import ThreadPoolExecutor, as_completed

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


def preprocess_image_v3(img, use_deskew=False, use_sharpen=True, use_nlm_denoise=True, remove_watermark=True, use_red_channel=True):
    """
    BEST preprocessing pipeline with:
    - RED CHANNEL extraction (best for sports betting images - +10.7% improvement)
    - Red watermark removal (@cappersfree)
    - Unsharp Masking (sharpen edges)
    - Non-Local Means Denoising (better noise removal)
    - Deskewing DISABLED by default (images are always straight)
    
    Plus all v2 improvements (Lanczos4, padding, gamma, CLAHE).
    """
    import cv2
    import numpy as np
    from PIL import Image
    
    # Convert Input to OpenCV format (BGR)
    if isinstance(img, np.ndarray):
        # Already numpy, assume BGR if 3 channels, or Grayscale
        cv_img = img.copy()
    else:
        # Assume PIL Image
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
    
    # 3. Convert to Grayscale - USE RED CHANNEL for best results
    if use_red_channel:
        # Red channel is index 2 in BGR format
        gray = cv_img[:, :, 2]
    else:
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


# --- TESSERACT USER DATA ---
USER_WORDS_PATH = os.path.join(TESSDATA_DIR, 'eng.user-words')
USER_PATTERNS_PATH = os.path.join(TESSDATA_DIR, 'eng.user-patterns')




# --- AI OCR IMPLEMENTATION ---

def remove_red_watermark(image_path):
    """
    Remove red watermark text (like @cappersfree) from image.
    Returns path to preprocessed temp file.
    """
    import cv2
    import numpy as np
    import tempfile
    
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    cv_img = np.array(img)
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
    
    # Convert to HSV for red detection
    hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
    
    # Red spans across hue 0 and 180 in HSV
    # Target: RGB(233, 9, 3) which is pure red
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
    
    # Replace red pixels with white
    cv_img[red_mask > 0] = [255, 255, 255]
    
    # Convert back to RGB and save
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    result = Image.fromarray(cv_img)
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        result.save(f.name)
        return f.name


def _resolve_image_path(image_path):
    """
    Resolve web paths like /static/temp_images/... to actual filesystem paths.
    Uses TEMP_IMG_DIR from config for correct path resolution.
    """
    # Already an absolute Windows path (e.g., 'D:\...')
    if re.match(r'^[A-Za-z]:', image_path):
        return image_path
    
    # Web path for temp images - resolve using TEMP_IMG_DIR
    if image_path.startswith('/static/temp_images/'):
        filename = image_path.split('/static/temp_images/')[-1]
        return os.path.join(TEMP_IMG_DIR, filename)
    
    # Other relative paths - resolve against BASE_DIR
    clean_path = image_path.lstrip('/').replace('/', os.sep)
    return os.path.join(BASE_DIR, clean_path)


def extract_text_ai(image_path, model="google/gemma-3-12b-it:free"):
    """
    Extracts text using Vision AI models.
    This is generally slower but much more accurate for complex layouts.
    Updated to enforce JSON output for resilience.
    """
    sys_path = _resolve_image_path(image_path)
    
    if not os.path.exists(sys_path):
        return f"[Error: Image not found at {sys_path}]"

    prompt = (
        "Extract all text from this image exactly as it appears. "
        "Return a JSON object with a single key 'text' containing the extracted string. "
        "Do not add any markdown formatting or commentary outside the JSON."
    )
    
    try:
        # Call Provider Pool (handles Cerebras/Mistral/Groq/OpenRouter)
        # Use single image
        response_json = pooled_completion(prompt, images=[sys_path], timeout=180)
        
        if not response_json:
            # Fallback to OpenRouter directly if pool fails
            response_json = openrouter_completion(prompt, model=model, images=[sys_path], timeout=180)
        
        # Parse the JSON response
        try:
            data = json.loads(response_json)
            return data.get("text", "")
        except json.JSONDecodeError:
            # Fallback if validation passed but structure is wrong (unlikely)
            return response_json
            
    except Exception as e:
        return f"[AI OCR Error: {str(e)}]"


def preprocess_for_ai(img):
    """
    LIGHTWEIGHT preprocessing for AI Vision models.
    AI models don't need heavy thresholding - just watermark removal and basic cleanup.
    """
    import cv2
    import numpy as np
    from PIL import Image
    
    # Convert to OpenCV
    if isinstance(img, np.ndarray):
        cv_img = img.copy()
    else:
        if img.mode != 'RGB':
            img = img.convert('RGB')
        cv_img = np.array(img)
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)

    # 1. REMOVE RED WATERMARK (fast HSV mask)
    hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask = cv2.bitwise_or(mask1, mask2)
    kernel = np.ones((3, 3), np.uint8)
    red_mask = cv2.dilate(red_mask, kernel, iterations=1)
    cv_img[red_mask > 0] = [255, 255, 255]

    # 2. SKIP expensive upscaling - AI handles low-res fine
    # Only resize if image is VERY small (< 400px width)
    if cv_img.shape[1] < 400:
        scale = 800 / cv_img.shape[1]
        cv_img = cv2.resize(cv_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)

    # 3. SKIP denoising - AI handles noise well
    # 4. SKIP sharpening - not needed for vision models

    return Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))


def check_local_confidence(pil_image):
    """
    Hybrid OCR: Run local Tesseract first.
    If it finds high-confidence betting keywords, return the text.
    Otherwise return None to trigger AI fallback.
    """
    try:
        # Fast local OCR
        text = pytesseract.image_to_string(pil_image, config='--psm 6').strip()
        
        if not text or len(text) < 10:
            return None
            
        # Keywords that strongly suggest a betting slip
        keywords = [
            'spread', 'moneyline', 'total', 'over', 'under', 
            'odds', 'parlay', 'teaser', 'wager', 'payout', 
            'bet id', 'straight bet', 'team prop', 'player prop',
            'points', 'rebounds', 'assists', 'touchdown'
        ]
        
        # Count hits
        text_lower = text.lower()
        hits = sum(1 for k in keywords if k in text_lower)
        
        # Heuristic: If we have 2+ betting keywords and reasonable length, trust it.
        # This saves 5-10s per image for "easy" clean screenshots.
        if hits >= 2 and len(text) > 40:
            logging.info(f"[Hybrid OCR] Local OCR Confident: {hits} keywords found")
            return text
            
        return None
    except Exception as e:
        logging.warning(f"[Hybrid OCR] Local check failed: {e}")
        return None


def extract_text_batch(image_paths, model="google/gemini-2.0-flash-exp:free", chunk_size=10):
    """
    OPTIMIZED batch OCR with:
    - Hybrid Mode: Tries local Tesseract first (Fast Path)
    - In-Memory Processing: No temp files (Zero-Copy)
    - True Parallelism: Distributes chunks across different AI models
    - Chunk Size: Reduced to 10 to prevent hallucination/mismatch errors.
    """
    import cv2
    import numpy as np

    # 1. Resolve all paths
    resolved_paths = [_resolve_image_path(p) for p in image_paths]
            
    valid_images = []
    indices_map = {}
    
    final_results = [""] * len(image_paths)
    
    # --- CACHING LAYER ---
    import hashlib
    CACHE_DIR = os.path.join(BASE_DIR, 'cache', 'ocr_hashes')
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    def get_image_hash(path):
        """Fast SHA256 hash of image file"""
        try:
            with open(path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except:
            return None

    # Identify which images need processing
    needs_processing = [] # list of (index, path, hash)
    
    logging.info(f"[OCR] Starting Hybrid Pipeline for {len(resolved_paths)} images...")
    
    for i, p in enumerate(resolved_paths):
        if not os.path.exists(p):
            logging.warning(f"[OCR] Skipping missing file: {p}")
            continue
            
        img_hash = get_image_hash(p)
        if img_hash:
            cache_path = os.path.join(CACHE_DIR, f"{img_hash}.txt")
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        cached_text = f.read()
                    if len(cached_text) > 5:
                        final_results[i] = cached_text
                        logging.debug(f"[OCR] Cache Hit for {os.path.basename(p)}")
                        continue
                except:
                    pass # Ignore cache read errors
        
        # If no cache or invalid, add to processing list
        needs_processing.append((i, p, img_hash))

    if not needs_processing:
        logging.info("[OCR] All images found in cache.")
        return final_results
        
    logging.info(f"[OCR] {len(image_paths) - len(needs_processing)} cached. Processing {len(needs_processing)} new images.")

    # Queue for AI processing
    ai_queue = [] # list of (original_index, pil_image, hash)
    
    # 2. SMART ROUTING: Use ImageClassifier to determine OCR strategy
    fallback_texts = {} # Store low-confidence local OCR as backup

    for i, p, img_hash in needs_processing:
        try:
            # Read Image
            img_cv = cv2.imread(p)
            if img_cv is None: continue
            
            # --- SMART CLASSIFIER: Analyze image to determine best OCR strategy ---
            analysis = ImageClassifier.classify_from_array(img_cv)
            
            if analysis.strategy == OCRStrategy.VISION_AI_REQUIRED:
                # Skip Tesseract entirely for complex/styled images
                logging.info(f"[Smart OCR] Vision AI required for {os.path.basename(p)}: {', '.join(analysis.reasons[:2])}")
                
                # Store empty fallback (no local OCR attempted)
                fallback_texts[i] = ""
                
                # Prepare for AI (Use lightweight preprocessing for Vision Models)
                pil_img = preprocess_for_ai(img_cv)
                ai_queue.append((i, pil_img, img_hash))
                continue
            
            # TESSERACT PATH: For clean, document-style images
            logging.info(f"[Smart OCR] Tesseract likely for {os.path.basename(p)} (confidence={analysis.confidence:.0%})")
            
            # Use Heavy Preprocessing for Tesseract
            heavy_img = preprocess_image_v3(img_cv)
            
            # Run Local OCR
            local_text = pytesseract.image_to_string(heavy_img, config='--psm 6').strip()
            
            # IMPROVED CONFIDENCE CHECK: Use classifier + keyword validation
            is_confident = False
            if local_text and len(local_text) > 10:
                keywords = [
                    'spread', 'moneyline', 'total', 'over', 'under', 
                    'odds', 'parlay', 'teaser', 'wager', 'payout', 
                    'bet id', 'straight bet', 'team prop', 'player prop',
                    'points', 'rebounds', 'assists', 'touchdown',
                    'win', 'loss', 'void', 'selection', 'risk', 'to win'
                ]
                text_lower = local_text.lower()
                hits = sum(1 for k in keywords if k in text_lower)
                
                # RELAXED: Since classifier already said Tesseract is likely, trust it more
                # Only need 1 keyword instead of 2
                if hits >= 1 and len(local_text) > 30:
                    is_confident = True
                    logging.info(f"[Hybrid OCR] Local OCR Confident: {hits} keywords, classifier approved")

            if is_confident:
                final_results[i] = local_text
                # Save to cache
                if img_hash:
                    with open(os.path.join(CACHE_DIR, f"{img_hash}.txt"), "w", encoding="utf-8") as f:
                        f.write(local_text)
            else:
                # Tesseract failed despite classifier prediction - fall back to AI
                logging.info(f"[Hybrid OCR] Tesseract output low quality, falling back to AI for {os.path.basename(p)}")
                fallback_texts[i] = local_text if local_text else ""
                
                # Prepare for AI (Use lightweight preprocessing for Vision Models)
                pil_img = preprocess_for_ai(img_cv)
                ai_queue.append((i, pil_img, img_hash))
                
        except Exception as e:
            logging.error(f"[OCR] Pre-check failed for {p}: {e}")
            
    # If all handled locally, we are done!
    if not ai_queue:
        logging.info("[OCR] All images handled by Local OCR (Fast Path).")
        return final_results
        
    logging.info(f"[OCR] AI Fallback required for {len(ai_queue)} images. Starting parallel processing...")
    
    # 3. AI Processing (Memory Optimized)
    
    # Helper to chunk the queue
    def get_chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]
            
    chunks = list(get_chunks(ai_queue, chunk_size))
    total_chunks = len(chunks)
    
    def process_ai_chunk(chunk_idx, chunk_data, assigned_model):
        """
        Process a chunk of (index, image, hash) tuples.
        Returns: [(index, text), ...]
        """
        try:
            # Convert images to base64 strings in memory
            b64_images = []
            for _, img, _ in chunk_data:
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                b64_images.append(img_str)
            
            prompt = (
                f"You are processing {len(b64_images)} distinct images. "
                f"Return a JSON array containing EXACTLY {len(b64_images)} strings. "
                "Index 0 corresponds to the first image, Index 1 to the second, etc. "
                "For each image, combine ALL text into a SINGLE string (use \\n for line breaks). "
                "Do NOT split an image's text into multiple array elements. "
                "Example Output: [\"Full text of image 1\", \"Full text of image 2\"]"
            )
            
            logging.info(f"[OCR] AI Chunk {chunk_idx+1}/{total_chunks} -> Pooled (Mistral/Groq/OpenRouter)")
            
            # Use pooled completion for batch processing (if provider supports it)
            # Currently our pool handles list of images by taking first one for single request
            # BUT here we are sending a batch of images.
            # Mistral/Groq client needs to support multiple images in one request?
            # Most APIs only support 1 image per request or text + multiple images.
            # Our prompt logic relies on OpenRouter's ability to handle multiple images.
            
            # For now, let's stick to OpenRouter for BATCHES because local providers often struggle with 10+ images.
            # Or we iterate?
            # Reverting to OpenRouter for safety on batches, OR we implement improved looping in pool.
            
            # Actually, standardizing on OpenRouter for massive batches is safer for now
            # as Mistral/Groq might have stricter limits or different multi-image formats.
            response = openrouter_completion(prompt, model=assigned_model, images=b64_images, timeout=180)
            
            if not response or len(response) < 50:
                logging.error(f"[OCR] AI returned empty/short response for chunk {chunk_idx}: {len(response) if response else 0} chars")
                raise Exception(f"Empty response from AI model")
            
            # Parse JSON
            clean_resp = response.strip()
            if clean_resp.startswith("```json"):
                clean_resp = clean_resp.split("```json")[1].split("```")[0].strip()
            elif clean_resp.startswith("```"):
                clean_resp = clean_resp.split("```")[1].split("```")[0].strip()
            
            results = []
            try:
                json_arr = json.loads(clean_resp)
                # Map back to original indices
                if isinstance(json_arr, list) and len(json_arr) == len(chunk_data):
                    for j, text in enumerate(json_arr):
                        orig_idx = chunk_data[j][0]
                        results.append((orig_idx, str(text)))
                else:
                    # Fallback if length mismatch
                    logging.warning(f"[OCR] Model {assigned_model} returned {len(json_arr)} items, expected {len(chunk_data)}")
                    # Try best fit
                    for j, item in enumerate(chunk_data):
                        txt = json_arr[j] if j < len(json_arr) else ""
                        results.append((item[0], str(txt)))
            except:
                 # Last resort: if single item
                if len(chunk_data) == 1:
                    results.append((chunk_data[0][0], clean_resp))
                else:
                    logging.error(f"[OCR] JSON Parse failed for chunk {chunk_idx}")
            
            return results
            
        except Exception as e:
            logging.error(f"[OCR] Chunk {chunk_idx} failed: {e}")
            return []

    # 4. Execute PARALLEL AI (Distributed across ALL providers)
    # We want to maximize throughput by using every available free tier simultaneously.
    
    PROVIDERS = [
        {"type": "local", "name": "mistral"}, # Mistral Pixtral
        {"type": "local", "name": "groq"},    # Groq Llama Vision
        {"type": "openrouter", "model": "google/gemini-2.0-flash-exp:free"},
        {"type": "openrouter", "model": "meta-llama/llama-3.2-90b-vision-instruct:free"},
        {"type": "openrouter", "model": "qwen/qwen-2.5-vl-7b-instruct:free"},
        {"type": "openrouter", "model": "nvidia/nemotron-nano-12b-v2-vl:free"}
    ]
    
    # Helper to process a chunk with a SPECIFIC provider
    def process_chunk_with_provider(chunk_idx, chunk_data, provider_config):
        provider_type = provider_config["type"]
        name = provider_config.get("name")
        model = provider_config.get("model")
        
        logging.info(f"[OCR] Chunk {chunk_idx+1} -> Assigned to {name or model}")
        
        try:
            # Convert images to base64
            b64_images = []
            for _, img, _ in chunk_data:
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                b64_images.append(img_str)
            
            prompt = (
                f"You are processing {len(b64_images)} distinct images. "
                f"Return a JSON array containing EXACTLY {len(b64_images)} strings. "
                "Index 0 corresponds to the first image, Index 1 to the second, etc. "
                "For each image, combine ALL text into a SINGLE string (use \\n for line breaks). "
                "Do NOT split an image's text into multiple array elements. "
                "Example Output: [\"Full text of image 1\", \"Full text of image 2\"]"
            )
            
            # Dispatch based on type
            response = None
            if provider_type == "local":
                # Use pooled_completion but FORCE the specific provider
                response = pooled_completion(prompt, images=b64_images, timeout=180, provider=name)
            else:
                # OpenRouter specific model
                response = pooled_completion(prompt, images=b64_images, timeout=180, model=model)
            
            if not response or len(response) < 50:
                raise Exception(f"Empty/Short response from {name or model}")
                
            # Parse JSON
            clean_resp = response.strip()
            if clean_resp.startswith("```json"):
                clean_resp = clean_resp.split("```json")[1].split("```")[0].strip()
            elif clean_resp.startswith("```"):
                clean_resp = clean_resp.split("```")[1].split("```")[0].strip()
                
            results = []
            try:
                json_arr = json.loads(clean_resp)
                if isinstance(json_arr, list) and len(json_arr) == len(chunk_data):
                    for j, text in enumerate(json_arr):
                        orig_idx = chunk_data[j][0]
                        results.append((orig_idx, str(text)))
                else:
                    logging.warning(f"[OCR] {name or model} returned {len(json_arr)} items, expected {len(chunk_data)}")
                    for j, item in enumerate(chunk_data):
                        txt = json_arr[j] if j < len(json_arr) else ""
                        results.append((item[0], str(txt)))
            except:
                if len(chunk_data) == 1:
                    results.append((chunk_data[0][0], clean_resp))
                else:
                    raise Exception("JSON Parse Failed")
            
            return results

        except Exception as e:
            logging.error(f"[OCR] Chunk {chunk_idx} failed with {name or model}: {e}")
            return None

    # Launch Parallel Execution
    # We map chunks to providers Round-Robin style
    with ThreadPoolExecutor(max_workers=len(PROVIDERS)) as executor:
        futures = {}
        for i, chunk in enumerate(chunks):
            # Pick provider based on index
            provider = PROVIDERS[i % len(PROVIDERS)]
            
            future = executor.submit(process_chunk_with_provider, i, chunk, provider)
            futures[future] = i
            
        for future in as_completed(futures):
            i = futures[future]
            try:
                chunk_results = future.result()
                if chunk_results:
                    for orig_idx, text in chunk_results:
                        if text and len(text) > 10 and "error" not in text.lower():
                            final_results[orig_idx] = text
                            
                            # SAVE TO CACHE
                            for c_idx, _, c_hash in chunks[i]:
                                if c_idx == orig_idx and c_hash:
                                    with open(os.path.join(CACHE_DIR, f"{c_hash}.txt"), "w", encoding="utf-8") as f:
                                        f.write(text)
                                    break
                        else:
                            # Use fallback
                            if orig_idx in fallback_texts:
                                final_results[orig_idx] = fallback_texts[orig_idx]
                else:
                    # Chunk failed completely, apply fallback to all
                    for orig_idx, _, _ in chunks[i]:
                        if orig_idx in fallback_texts:
                            final_results[orig_idx] = fallback_texts[orig_idx]
            except Exception as e:
                logging.error(f"[OCR] Future failed: {e}")
                for orig_idx, _, _ in chunks[i]:
                    if orig_idx in fallback_texts:
                        final_results[orig_idx] = fallback_texts[orig_idx]

    # Final Sweep: Apply fallback to any images that went to AI but have empty results
    for i, _, _ in ai_queue:
        if not final_results[i] or len(final_results[i]) < 5:
            if i in fallback_texts and len(fallback_texts[i]) > 5:
                 final_results[i] = fallback_texts[i]
                 logging.info(f"[OCR] Using local fallback for failed AI image {i}")

    # --- TWO-PASS VERIFICATION (DeepSeek Chimera Logic) ---
    # Check for low-confidence results and retry with stronger model
    retry_indices = []
    
    for i, text in enumerate(final_results):
        # Don't verify empty/skipped results
        if not text: continue
            
        if not TwoPassVerifier.verify_ocr_result(text):
            retry_indices.append(i)
            
    if retry_indices:
        logging.info(f"[OCR] Two-Pass Verification: {len(retry_indices)} images flagged for retry with Strong Vision Model.")
        
        # Prepare retry batch
        # We need the original paths
        retry_paths = [resolved_paths[i] for i in retry_indices]
        
        # Use simple sequential processing for retry (it's usually small)
        strong_model = TwoPassVerifier.get_strong_vision_model()
        
        for idx, path in zip(retry_indices, retry_paths):
            try:
                # Use extract_text_ai with explicit model
                logging.info(f"[OCR] Retrying Image {idx} with {strong_model}...")
                
                # --- STRATEGY UPDATE: Use One-Shot Vision Parsing for Retry ---
                # Instead of asking for raw text (which can still be messy), ask for JSON structure
                # and then reconstruct the text. This forces the model to interpret the layout.
                
                structured_picks = parse_image_direct(path)
                
                if structured_picks:
                    # Reconstruct text from JSON
                    lines = []
                    for p in structured_picks:
                        # Format: "Lakers -5 -110 (1.0u)"
                        line = f"{p.get('pick', '')} {p.get('odds', '')} ({p.get('units', '')}u)"
                        if p.get('capper_name') != "Unknown":
                            line = f"{p.get('capper_name')} " + line
                        lines.append(line)
                    
                    retry_text = "\n".join(lines)
                    logging.info(f"[OCR] One-Shot Retry generated {len(lines)} structured lines.")
                else:
                    # Fallback to standard raw text extraction if One-Shot fails
                    retry_text = extract_text_ai(path, model=strong_model)
                
                if TwoPassVerifier.verify_ocr_result(retry_text):
                    final_results[idx] = retry_text
                    logging.info(f"[OCR] Retry Success for Image {idx}")
                    
                    # Update Cache if possible
                    try:
                        # We need the hash again. We can re-calc or lookup.
                        # We have 'needs_processing' but indices might not align if some were cached.
                        # It's safer to just re-calc hash for this specific file
                        import hashlib
                        with open(path, "rb") as f:
                            h = hashlib.sha256(f.read()).hexdigest()
                        
                        cache_path = os.path.join(CACHE_DIR, f"{h}.txt")
                        with open(cache_path, "w", encoding="utf-8") as f:
                            f.write(retry_text)
                    except Exception as e:
                        logging.warning(f"[OCR] Failed to update cache for retry: {e}")
                else:
                    logging.warning(f"[OCR] Retry Failed for Image {idx} (still low confidence)")
            except Exception as e:
                logging.error(f"[OCR] Retry Exception for Image {idx}: {e}")

    return final_results


def extract_text(image_relative_path):
    """
    Main entry point for OCR.
    NOW DEFAULTS TO AI_OCR.
    """
    return extract_text_ai(image_relative_path)


# --- LOCAL TESSERACT FUNCTIONS (for benchmarking) ---

def extract_text_simple_tesseract(image_path):
    """
    Simple local Tesseract OCR with NO preprocessing.
    Used for baseline benchmark comparison.
    """
    try:
        img = Image.open(image_path)
        # Direct OCR with default settings
        text = pytesseract.image_to_string(img, config='--psm 6')
        return text.strip()
    except Exception as e:
        logging.error(f"[Simple Tesseract] Error: {e}")
        return f"[Error: {str(e)}]"


def extract_text_v3(image_path):
    """
    Local Tesseract OCR with V3 preprocessing (best preprocessing pipeline).
    Used for benchmark comparison.
    """
    import cv2
    import numpy as np
    
    try:
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            return "[Error: Could not read image]"
        
        # Apply V3 preprocessing
        processed = preprocess_image_v3(img)
        
        # OCR with user words if available
        config = '--psm 6'
        if os.path.exists(USER_WORDS_PATH):
            config += f' --user-words {USER_WORDS_PATH}'
        if os.path.exists(USER_PATTERNS_PATH):
            config += f' --user-patterns {USER_PATTERNS_PATH}'
        
        text = pytesseract.image_to_string(processed, config=config)
        return text.strip()
    except Exception as e:
        logging.error(f"[Tesseract V3] Error: {e}")
        return f"[Error: {str(e)}]"



