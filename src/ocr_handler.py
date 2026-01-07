
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
from src.openrouter_client import openrouter_completion

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


def extract_text_ai(image_path, model="google/gemma-3-12b-it:free"):
    """
    Extracts text using Vision AI models.
    This is generally slower but much more accurate for complex layouts.
    """
    # Handle path resolution
    # On Windows, os.path.isabs('/static/...') returns True (relative to drive root)
    # but we want to treat paths starting with '/' as relative to BASE_DIR
    is_windows_absolute = bool(re.match(r'^[A-Za-z]:', image_path))
    
    if is_windows_absolute:
        sys_path = image_path
    else:
        clean_path = image_path.lstrip('/').replace('/', os.sep)
        sys_path = os.path.join(BASE_DIR, clean_path)
    
    if not os.path.exists(sys_path):
        return f"[Error: Image not found at {sys_path}]"

    prompt = "Extract all text from this image exactly as it appears. Do not add any markdown formatting or commentary. Just return the text."
    
    try:
        # Call OpenRouter with image
        text = openrouter_completion(prompt, model=model, images=[sys_path])
        return text
    except Exception as e:
        return f"[AI OCR Error: {str(e)}]"


def extract_text_batch(image_paths, model="google/gemma-3-12b-it:free"):
    """
    Batch processing for AI OCR.
    Extracts text from multiple images in a single API call (up to 32 images).
    Returns a list of strings corresponding to the input images.
    """
    # 1. Resolve all paths
    resolved_paths = []
    for p in image_paths:
        # On Windows, os.path.isabs('/static/...') returns True (relative to drive root)
        # but we want to treat paths starting with '/' as relative to BASE_DIR
        # Only treat as absolute if it has a drive letter (e.g., 'C:\...' or 'D:\...')
        is_windows_absolute = bool(re.match(r'^[A-Za-z]:', p))
        
        if is_windows_absolute:
            resolved_paths.append(p)
        else:
            clean = p.lstrip('/').replace('/', os.sep)
            resolved_paths.append(os.path.join(BASE_DIR, clean))
            
    # Verify existence
    valid_images = []
    indices_map = {} # Maps batch index to original index
    
    for i, p in enumerate(resolved_paths):
        if os.path.exists(p):
            valid_images.append(p)
            indices_map[len(valid_images)-1] = i
        else:
            print(f"[Warning] Batch OCR skipping missing file: {p}")
            
    if not valid_images:
        return [""] * len(image_paths)
    
    # 2. Apply red watermark removal preprocessing
    preprocessed_images = []
    temp_files = []
    for img_path in valid_images:
        try:
            temp_path = remove_red_watermark(img_path)
            preprocessed_images.append(temp_path)
            temp_files.append(temp_path)
        except Exception as e:
            logging.warning(f"[OCR] Preprocessing failed for {img_path}: {e}")
            preprocessed_images.append(img_path)  # Use original on failure

    # 3. Build Prompt - Keep it concise to reduce token usage
    prompt = (
        f"OCR task: {len(preprocessed_images)} images. "
        "Extract text from each. Return JSON array of strings only. "
        "No explanations. Format: [\"text1\", \"text2\", ...]"
    )

    MAX_RETRIES = 3
    RETRY_DELAY = 2

    for attempt in range(MAX_RETRIES):
        try:
            # Call OpenRouter with preprocessed images
            response = openrouter_completion(prompt, model=model, images=preprocessed_images, timeout=120)
            
            # Parse JSON
            clean_resp = response.strip()
            if clean_resp.startswith("```json"):
                clean_resp = clean_resp.split("```json")[1].split("```")[0].strip()
            elif clean_resp.startswith("```"):
                clean_resp = clean_resp.split("```")[1].split("```")[0].strip()
                
            try:
                results = json.loads(clean_resp)
                # If success, break loop
                break
            except json.JSONDecodeError:
                # Fallback 1: Try to fix truncated JSON array
                if clean_resp.startswith('['):
                    # Find last complete string in array
                    try:
                        # Try to close the array properly
                        # Find last complete quoted string
                        import re as regex_module
                        # Match complete strings in array format
                        string_pattern = r'"([^"\\]|\\.)*"'
                        matches = list(regex_module.finditer(string_pattern, clean_resp))
                        if matches:
                            last_match = matches[-1]
                            # Reconstruct valid JSON up to last complete string
                            fixed_json = clean_resp[:last_match.end()]
                            # Close the array
                            if not fixed_json.rstrip().endswith(']'):
                                fixed_json = fixed_json.rstrip().rstrip(',') + ']'
                            try:
                                results = json.loads(fixed_json)
                                logging.info(f"[AI Batch OCR] Recovered {len(results)} results from truncated JSON")
                                break
                            except:
                                results = None
                        else:
                            results = None
                    except:
                        results = None
                else:
                    results = None
                
                # Fallback 2: If still no results, try to use raw text for single image case
                if results is None:
                    if len(preprocessed_images) == 1:
                        # For single image, just use the raw response as text
                        logging.warning("[AI Batch OCR] Using raw response as text for single image")
                        results = [clean_resp]
                        break
                    else:
                        logging.error(f"[AI Batch OCR] JSON Decode Failed (Attempt {attempt+1}/{MAX_RETRIES}). Raw: {clean_resp[:300]}")
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(RETRY_DELAY * (attempt + 1))
                            continue
                        return [""] * len(image_paths)  # Return empty strings instead of error
                
        except Exception as e:
            logging.error(f"[AI Batch OCR] Exception (Attempt {attempt+1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                return [f"[Error: {str(e)}]"] * len(image_paths)
            
    # Map back to original list
    final_output = [""] * len(image_paths)
    
    for batch_idx, text in enumerate(results):
        if batch_idx in indices_map:
            orig_idx = indices_map[batch_idx]
            if orig_idx < len(final_output):
                final_output[orig_idx] = str(text)
                
    # Clean up temp files
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        except Exception:
            pass

    return final_output


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


def extract_text_batch_v3_ai(image_paths, model="google/gemma-3-12b-it:free"):
    """
    Pipeline D: Batch processing for AI OCR with V3 Preprocessing.
    Applies preprocess_image_v3 (Red Channel + Upscale + Denoise) before AI.
    """
    import tempfile
    import cv2
    import numpy as np

    # 1. Resolve all paths (same as standard batch)
    resolved_paths = []
    for p in image_paths:
        is_windows_absolute = bool(re.match(r'^[A-Za-z]:', p))
        if is_windows_absolute:
            resolved_paths.append(p)
        else:
            clean = p.lstrip('/').replace('/', os.sep)
            resolved_paths.append(os.path.join(BASE_DIR, clean))
            
    # Verify existence
    valid_images = []
    indices_map = {} # Maps batch index to original index
    
    for i, p in enumerate(resolved_paths):
        if os.path.exists(p):
            valid_images.append(p)
            indices_map[len(valid_images)-1] = i
        else:
            print(f"[Warning] Batch OCR V3 skipping missing file: {p}")
            
    if not valid_images:
        return [""] * len(image_paths)
    
    # 2. Apply V3 PREPROCESSING
    preprocessed_images = []
    temp_files = []
    
    for img_path in valid_images:
        try:
            # Read image with OpenCV
            img = cv2.imread(img_path)
            if img is not None:
                # Apply V3 pipeline
                processed_pil = preprocess_image_v3(img)
                
                # Save to temp file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                    processed_pil.save(f.name)
                    preprocessed_images.append(f.name)
                    temp_files.append(f.name)
            else:
                logging.warning(f"[OCR V3] Could not read {img_path}")
                preprocessed_images.append(img_path) # Fallback to original
                
        except Exception as e:
            logging.warning(f"[OCR V3] Preprocessing failed for {img_path}: {e}")
            preprocessed_images.append(img_path)  # Use original on failure

    # 3. Build Prompt (Same as standard batch)
    prompt = (
        f"OCR task: {len(preprocessed_images)} images. "
        "Extract text from each. Return JSON array of strings only. "
        "No explanations. Format: [\"text1\", \"text2\", ...]"
    )

    MAX_RETRIES = 3
    RETRY_DELAY = 2

    for attempt in range(MAX_RETRIES):
        try:
            # Call OpenRouter with preprocessed images
            response = openrouter_completion(prompt, model=model, images=preprocessed_images, timeout=120)
            
            # Parse JSON - Logic duplicated from extract_text_batch to keep self-contained or could be shared
            clean_resp = response.strip()
            if clean_resp.startswith("```json"):
                clean_resp = clean_resp.split("```json")[1].split("```")[0].strip()
            elif clean_resp.startswith("```"):
                clean_resp = clean_resp.split("```")[1].split("```")[0].strip()
                
            try:
                results = json.loads(clean_resp)
                break
            except json.JSONDecodeError:
                # Fallback 1: Fix truncated JSON
                if clean_resp.startswith('['):
                    try:
                        import re as regex_module
                        string_pattern = r'"([^"\\]|\\.)*"'
                        matches = list(regex_module.finditer(string_pattern, clean_resp))
                        if matches:
                            last_match = matches[-1]
                            fixed_json = clean_resp[:last_match.end()]
                            if not fixed_json.rstrip().endswith(']'):
                                fixed_json = fixed_json.rstrip().rstrip(',') + ']'
                            try:
                                results = json.loads(fixed_json)
                                logging.info(f"[AI Batch OCR V3] Recovered {len(results)} results")
                                break
                            except:
                                results = None
                        else:
                            results = None
                    except:
                        results = None
                else:
                    results = None
                
                # Fallback 2: Raw text for single image
                if results is None:
                    if len(preprocessed_images) == 1:
                        logging.warning("[AI Batch OCR V3] Using raw response for single image")
                        results = [clean_resp]
                        break
                    else:
                        logging.error(f"[AI Batch OCR V3] JSON Decode Failed (Attempt {attempt+1}). Raw: {clean_resp[:300]}")
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(RETRY_DELAY * (attempt + 1))
                            continue
                        return [""] * len(image_paths)
                
        except Exception as e:
            logging.error(f"[AI Batch OCR V3] Exception (Attempt {attempt+1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                return [f"[Error: {str(e)}]"] * len(image_paths)
            
    # Map back to original list
    final_output = [""] * len(image_paths)
    for batch_idx, text in enumerate(results):
        if batch_idx in indices_map:
            orig_idx = indices_map[batch_idx]
            if orig_idx < len(final_output):
                final_output[orig_idx] = str(text)
                
    # Clean up temp files
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        except Exception:
            pass

    return final_output
