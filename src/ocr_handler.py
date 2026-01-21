
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
from config import TEMP_IMG_DIR

# Import Preprocessing (Backward Compatibility)
from src.ocr_preprocessing import (
    preprocess_image, preprocess_image_v2, preprocess_image_v3, 
    deskew_image, remove_red_watermark
)

# Import Cascade
from src.ocr_cascade import extract_text_cascade, extract_batch_cascade, OCRResult, OCRMethod

# --- CONFIGURATION ---
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TESSDATA_DIR = os.path.join(BASE_DIR, 'tessdata')

if sys.platform == 'win32':
    TESSERACT_BIN = os.path.join(BASE_DIR, 'bin', 'win', 'tesseract.exe')
else:
    TESSERACT_BIN = os.path.join(BASE_DIR, 'bin', 'mac', 'tesseract')

if sys.platform == 'darwin':
    mac_bin_folder = os.path.dirname(TESSERACT_BIN)
    current_path = os.environ.get('DYLD_LIBRARY_PATH', '')
    os.environ['DYLD_LIBRARY_PATH'] = f"{mac_bin_folder}:{current_path}"
    if os.path.exists(mac_bin_folder):
        for filename in os.listdir(mac_bin_folder):
            filepath = os.path.join(mac_bin_folder, filename)
            try:
                st = os.stat(filepath)
                os.chmod(filepath, st.st_mode | stat.S_IEXEC)
            except Exception:
                pass

if os.path.exists(TESSDATA_DIR):
    os.environ['TESSDATA_PREFIX'] = TESSDATA_DIR
elif os.path.exists('/opt/homebrew/share/tessdata'):
    TESSDATA_DIR = '/opt/homebrew/share/tessdata'
    os.environ['TESSDATA_PREFIX'] = TESSDATA_DIR
elif os.path.exists('/usr/local/share/tessdata'):
    TESSDATA_DIR = '/usr/local/share/tessdata'
    os.environ['TESSDATA_PREFIX'] = TESSDATA_DIR

if os.path.exists(TESSERACT_BIN):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_BIN
else:
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

# --- HELPERS ---

def _resolve_image_path(image_path):
    """
    Resolve web paths like /static/temp_images/... to actual filesystem paths.
    """
    if re.match(r'^[A-Za-z]:', image_path):
        return image_path
    
    if image_path.startswith('/static/temp_images/'):
        filename = image_path.split('/static/temp_images/')[-1]
        return os.path.join(TEMP_IMG_DIR, filename)
    
    clean_path = image_path.lstrip('/').replace('/', os.sep)
    return os.path.join(BASE_DIR, clean_path)

# --- MAIN FUNCTIONS ---

def extract_text(image_path):
    """
    Main entry point for single image OCR.
    Delegates to Smart OCR Cascade.
    """
    sys_path = _resolve_image_path(image_path)
    return extract_text_cascade(sys_path, prompt_type="structured")

def extract_text_batch(image_paths, model="google/gemini-2.0-flash-exp:free", chunk_size=10):
    """
    Batch OCR using Smart Cascade.
    Preserves existing Caching Layer.
    """
    # 1. Resolve all paths
    resolved_paths = [_resolve_image_path(p) for p in image_paths]
    
    final_results = [""] * len(image_paths)
    
    # --- CACHING LAYER ---
    import hashlib
    CACHE_DIR = os.path.join(BASE_DIR, 'cache', 'ocr_hashes')
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    def get_image_hash(path):
        try:
            with open(path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except:
            return None

    # Identify which images need processing
    needs_processing = [] # list of (index, path, hash)
    
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
                        continue
                except:
                    pass 
        
        needs_processing.append((i, p, img_hash))
    
    if not needs_processing:
        return final_results
        
    logging.info(f"[OCR] Processing {len(needs_processing)} new images with Cascade...")
    
    # Process new images with Cascade
    new_paths = [p for _, p, _ in needs_processing]
    
    # Use Cascade Batch
    cascade_results = extract_batch_cascade(new_paths, prompt_type="structured")
    
    # Map results back
    for j, result_text in enumerate(cascade_results):
        orig_idx, _, img_hash = needs_processing[j]
        final_results[orig_idx] = result_text
        
        # Update Cache
        if img_hash and result_text and len(result_text) > 5:
            try:
                with open(os.path.join(CACHE_DIR, f"{img_hash}.txt"), "w", encoding="utf-8") as f:
                    f.write(result_text)
            except Exception as e:
                logging.warning(f"[OCR] Cache write failed: {e}")
    
    return final_results

# --- LEGACY / BENCHMARKING FUNCTIONS ---
# Kept for compatibility with benchmark scripts that might import them

def extract_text_simple_tesseract(image_path):
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, config='--psm 6')
        return text.strip()
    except Exception as e:
        return f"[Error: {str(e)}]"

def extract_text_v3(image_path):
    try:
        # Re-implement using imported preprocessing
        import cv2
        img = cv2.imread(image_path)
        if img is None: return "[Error]"
        processed = preprocess_image_v3(img)
        text = pytesseract.image_to_string(processed, config='--psm 6')
        return text.strip()
    except Exception as e:
        return f"[Error: {str(e)}]"

# Alias for backward compatibility
extract_text_ai = extract_text 
