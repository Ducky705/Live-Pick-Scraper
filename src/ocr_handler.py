
# src/ocr_handler.py
"""
OCR Handler - Primary OCR interface for the TelegramScraper.

Delegates all logic to the Unified OCR Cascade Engine (src/ocr_cascade.py).
This ensures consistent behavior across the application.
"""

from PIL import Image
import os
import sys
import logging
import cv2
import numpy as np
from src.ocr_preprocessing import preprocess_for_rapidocr
from src.ocr_cascade import extract_text_cascade, extract_batch_cascade
from config import TEMP_IMG_DIR

# --- CONFIGURATION ---
if getattr(sys, 'frozen', False):
    # Running as compiled APP
    BASE_DIR = sys._MEIPASS
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- COMPATIBILITY WRAPPERS (Deprecated) ---

def preprocess_image(img):
    """Deprecated: Use src.ocr_preprocessing directly."""
    return Image.fromarray(preprocess_for_rapidocr(img))

def preprocess_image_v2(img):
    """Deprecated: Use src.ocr_preprocessing directly."""
    return Image.fromarray(preprocess_for_rapidocr(img))

def preprocess_image_v3(img, **kwargs):
    """Deprecated: Use src.ocr_preprocessing directly."""
    return Image.fromarray(preprocess_for_rapidocr(img))

# --- MAIN OCR INTERFACE ---

def extract_text(image_relative_path):
    """
    Extract text from a single image using the Smart OCR Cascade.
    """
    try:
        return extract_text_cascade(image_relative_path)
    except Exception as e:
        logging.error(f"[OCR Handler] Error in extract_text: {e}")
        return f"[Error: {str(e)}]"

def extract_text_batch(image_paths, model=None, chunk_size=None):
    """
    Extract text from multiple images using the Smart OCR Cascade (Batch Mode).
    
    Args:
        image_paths: List of file paths
        model: Ignored (managed by Cascade)
        chunk_size: Ignored (managed by Cascade)
        
    Returns:
        List of extracted text strings
    """
    try:
        return extract_batch_cascade(image_paths)
    except Exception as e:
        logging.error(f"[OCR Handler] Error in extract_text_batch: {e}")
        # Return empty strings for failed batch to prevent crash
        return [""] * len(image_paths)

# --- UTILS (Kept if external dependencies exist) ---

def _resolve_image_path(image_path):
    """Resolve paths (internal helper)."""
    import re
    if re.match(r'^[A-Za-z]:', image_path):
        return image_path
    if image_path.startswith('/static/temp_images/'):
        filename = image_path.split('/static/temp_images/')[-1]
        return os.path.join(TEMP_IMG_DIR, filename)
    clean_path = image_path.lstrip('/').replace('/', os.sep)
    return os.path.join(BASE_DIR, clean_path)

# --- DEPRECATED/LEGACY FUNCTIONS ---
# These are kept as stubs to prevent import errors if older code calls them.

def extract_text_ai(image_path, model=None):
    """Deprecated: Use extract_text() instead."""
    return extract_text(image_path)

def check_local_confidence(pil_image):
    """Deprecated: Logic moved to OCRCascade."""
    return None

def remove_red_watermark(image_path):
    """Legacy helper."""
    # This logic is now inside preprocess_for_rapidocr / preprocess_for_ai
    # We can keep a minimal implementation or import it if needed.
    pass 
