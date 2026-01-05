# Quick test of Gaussian Adaptive Threshold output quality
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import pytesseract
import cv2
import numpy as np
from src.ocr_handler import TESSERACT_BIN
import os

if os.path.exists(TESSERACT_BIN):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_BIN

def preprocess_adaptive_gaussian(img):
    if img.mode != 'RGB':
        img = img.convert('RGB')
    cv_img = np.array(img)
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
    
    min_width = 1600
    if cv_img.shape[1] < min_width:
        scale = min_width / cv_img.shape[1]
        cv_img = cv2.resize(cv_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    
    pad = 50
    cv_img = cv2.copyMakeBorder(cv_img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (0, 0), 3)
    gray = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    # Gaussian adaptive threshold
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    white_ratio = np.sum(binary == 255) / binary.size
    if white_ratio < 0.3:
        binary = cv2.bitwise_not(binary)
    
    return Image.fromarray(binary)

# Test on one image
test_img = Path(__file__).parent / "samples" / "-1001900292133_55832.jpg"
img = Image.open(test_img)
processed = preprocess_adaptive_gaussian(img)
text = pytesseract.image_to_string(processed, config='--psm 6 --oem 3')
print("="*60)
print("GAUSSIAN ADAPTIVE THRESHOLD OUTPUT:")
print("="*60)
print(text[:500])
print("...")
print(f"\nTotal chars: {len(text)}, Words: {len(text.split())}")
