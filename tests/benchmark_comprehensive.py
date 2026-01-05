# tests/benchmark_comprehensive.py
"""
Comprehensive OCR Benchmark - Tests ALL preprocessing and OCR engine variants.
"""

import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import pytesseract
import cv2
import numpy as np

from src.ocr_handler import (
    preprocess_image, 
    preprocess_image_v2, 
    preprocess_image_v3,
    TESSERACT_BIN
)

if os.path.exists(TESSERACT_BIN):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_BIN

# Try to import EasyOCR
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    # Initialize once (slow first load)
    EASYOCR_READER = None
except ImportError:
    EASYOCR_AVAILABLE = False
    EASYOCR_READER = None


def get_easyocr_reader():
    """Lazy load EasyOCR reader."""
    global EASYOCR_READER
    if EASYOCR_READER is None and EASYOCR_AVAILABLE:
        print("  [Loading EasyOCR model...]")
        EASYOCR_READER = easyocr.Reader(['en'], gpu=False, verbose=False)
    return EASYOCR_READER


def post_process_text(text: str) -> str:
    """
    Post-processing to fix common OCR errors.
    """
    if not text:
        return text
    
    # Common OCR substitutions
    replacements = [
        # Sports betting specific
        (r'\bM[lI1]\b', 'ML'),  # ML (moneyline)
        (r'\b0ver\b', 'Over'),
        (r'\bUnder\b', 'Under'),
        (r'\b(\d+)[oO](\d+)\b', r'\1.0\2'),  # Fix decimal points
        # Common letter substitutions
        (r'[|!l](?=\d)', '1'),  # | or l before digit -> 1
        (r'(?<=\d)[oO](?=\d)', '0'),  # o between digits -> 0
        # Clean up garbage
        (r'[^\w\s\+\-\.\/@#$%&*()]+', ' '),  # Remove weird chars
        (r'\s+', ' '),  # Collapse whitespace
    ]
    
    result = text
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result.strip()


def preprocess_with_inpainting(img, remove_watermark=True):
    """
    Alternative watermark removal using inpainting instead of white fill.
    """
    if img.mode != 'RGB':
        img = img.convert('RGB')
    cv_img = np.array(img)
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
    
    if remove_watermark:
        hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
        
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)
        
        kernel = np.ones((3, 3), np.uint8)
        red_mask = cv2.dilate(red_mask, kernel, iterations=2)
        
        # Use inpainting instead of white fill
        cv_img = cv2.inpaint(cv_img, red_mask, 3, cv2.INPAINT_TELEA)
    
    return Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))


def preprocess_adaptive_gaussian(img):
    """Preprocessing with Gaussian adaptive threshold instead of Otsu."""
    if img.mode != 'RGB':
        img = img.convert('RGB')
    cv_img = np.array(img)
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
    
    # Upscale
    min_width = 1600
    if cv_img.shape[1] < min_width:
        scale = min_width / cv_img.shape[1]
        cv_img = cv2.resize(cv_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    
    # Padding
    pad = 50
    cv_img = cv2.copyMakeBorder(cv_img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    
    # Sharpen
    blurred = cv2.GaussianBlur(gray, (0, 0), 3)
    gray = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)
    
    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    # Gaussian adaptive threshold (instead of Otsu)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # Invert if needed
    white_ratio = np.sum(binary == 255) / binary.size
    if white_ratio < 0.3:
        binary = cv2.bitwise_not(binary)
    
    return Image.fromarray(binary)


def run_tesseract(img, oem=3, psm=6):
    """Run Tesseract with specific OEM/PSM."""
    config = f'--psm {psm} --oem {oem}'
    return pytesseract.image_to_string(img, config=config).strip()


def run_easyocr(img):
    """Run EasyOCR on image."""
    reader = get_easyocr_reader()
    if reader is None:
        return "[EasyOCR not available]"
    
    # Convert PIL to numpy
    img_np = np.array(img)
    if len(img_np.shape) == 2:
        # Grayscale - convert to RGB
        img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB)
    
    results = reader.readtext(img_np, detail=0)
    return ' '.join(results)


def get_samples():
    manifest_path = Path(__file__).parent / "manifest.json"
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def benchmark_single(name: str, preprocess_func, ocr_func, post_process=False, **kwargs):
    """Benchmark a single configuration."""
    cases = get_samples()
    base_dir = Path(__file__).parent.parent
    
    total_chars = 0
    total_words = 0
    errors = 0
    
    for case in cases:
        image_file = case.get("image_file", "")
        if not image_file:
            continue
        
        image_path = base_dir / "tests" / image_file
        if not image_path.exists():
            errors += 1
            continue
        
        try:
            img = Image.open(image_path)
            
            if preprocess_func:
                processed = preprocess_func(img, **kwargs) if kwargs else preprocess_func(img)
            else:
                processed = img
            
            text = ocr_func(processed)
            
            if post_process:
                text = post_process_text(text)
            
            total_chars += len(text)
            total_words += len(text.split())
            
        except Exception as e:
            errors += 1
    
    return {
        "name": name,
        "total_chars": total_chars,
        "total_words": total_words,
        "errors": errors,
        "samples": len(cases)
    }


def main():
    print("\n" + "="*80)
    print("  🔬 COMPREHENSIVE OCR BENCHMARK")
    print("="*80)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  EasyOCR available: {EASYOCR_AVAILABLE}")
    print("="*80)
    
    # Define all configurations to test
    configs = [
        # Baseline
        ("1. Baseline (v1 + Tesseract OEM3)", preprocess_image, lambda img: run_tesseract(img, oem=3), False, {}),
        
        # OEM modes
        ("2. v3 + Tesseract OEM 3 (default)", preprocess_image_v3, lambda img: run_tesseract(img, oem=3), False, {}),
        ("3. v3 + Tesseract OEM 1 (LSTM only)", preprocess_image_v3, lambda img: run_tesseract(img, oem=1), False, {}),
        
        # Post-processing
        ("4. v3 + OEM3 + Post-process", preprocess_image_v3, lambda img: run_tesseract(img, oem=3), True, {}),
        
        # Adaptive threshold
        ("5. Gaussian Adaptive Threshold", preprocess_adaptive_gaussian, lambda img: run_tesseract(img, oem=3), False, {}),
        
        # Inpainting watermark removal
        ("6. Inpainting Watermark + v3", lambda img: preprocess_image_v3(preprocess_with_inpainting(img)), lambda img: run_tesseract(img, oem=3), False, {}),
    ]
    
    # Add EasyOCR if available
    if EASYOCR_AVAILABLE:
        configs.extend([
            ("7. EasyOCR (no preprocess)", None, run_easyocr, False, {}),
            ("8. v3 preprocess + EasyOCR", preprocess_image_v3, run_easyocr, False, {}),
            ("9. EasyOCR + Post-process", None, run_easyocr, True, {}),
        ])
    
    results = []
    
    for name, preprocess_func, ocr_func, post_process, kwargs in configs:
        print(f"\n📊 Testing: {name}...")
        result = benchmark_single(name, preprocess_func, ocr_func, post_process, **kwargs)
        results.append(result)
        print(f"   Chars: {result['total_chars']:,}  |  Words: {result['total_words']:,}  |  Errors: {result['errors']}")
    
    # Sort by words
    results.sort(key=lambda x: x['total_words'], reverse=True)
    
    # Print final table
    print("\n" + "="*80)
    print("  FINAL RESULTS (sorted by word count)")
    print("="*80)
    print(f"{'#':<3} {'Configuration':<45} {'Chars':>10} {'Words':>10}")
    print("-"*80)
    
    baseline_words = next((r['total_words'] for r in results if 'Baseline' in r['name']), 0)
    
    for i, r in enumerate(results, 1):
        delta = r['total_words'] - baseline_words
        delta_str = f"(+{delta})" if delta > 0 else f"({delta})" if delta < 0 else ""
        print(f"{i:<3} {r['name']:<45} {r['total_chars']:>10,} {r['total_words']:>10,} {delta_str}")
    
    print("="*80)
    
    # Save results
    output_dir = Path(__file__).parent.parent / "benchmark_results"
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "comprehensive_benchmark.json", 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results
        }, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_dir / 'comprehensive_benchmark.json'}")
    
    # Best config
    best = results[0]
    print(f"\n🏆 BEST: {best['name']}")
    print(f"   {best['total_words']} words (+{best['total_words'] - baseline_words} vs baseline)")


if __name__ == "__main__":
    main()
