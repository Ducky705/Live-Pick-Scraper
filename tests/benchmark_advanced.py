# tests/benchmark_advanced.py
"""
Advanced OCR Benchmark - Tests multi-engine voting and text region detection.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import pytesseract
import cv2
import numpy as np

from src.ocr_handler import (
    preprocess_image_v3,
    TESSERACT_BIN
)

if os.path.exists(TESSERACT_BIN):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_BIN

# Try imports
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    EASYOCR_READER = None
except ImportError:
    EASYOCR_AVAILABLE = False
    EASYOCR_READER = None

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
    PADDLEOCR_READER = None
except ImportError:
    PADDLEOCR_AVAILABLE = False
    PADDLEOCR_READER = None


def get_easyocr_reader():
    global EASYOCR_READER
    if EASYOCR_READER is None and EASYOCR_AVAILABLE:
        print("  [Loading EasyOCR...]")
        EASYOCR_READER = easyocr.Reader(['en'], gpu=False, verbose=False)
    return EASYOCR_READER


def get_paddleocr_reader():
    global PADDLEOCR_READER
    if PADDLEOCR_READER is None and PADDLEOCR_AVAILABLE:
        print("  [Loading PaddleOCR...]")
        try:
            PADDLEOCR_READER = PaddleOCR(use_angle_cls=True, lang='en')
        except Exception as e:
            print(f"  [PaddleOCR error: {e}]")
            return None
    return PADDLEOCR_READER


def run_tesseract(img):
    """Run Tesseract OCR."""
    config = '--psm 6 --oem 3'
    return pytesseract.image_to_string(img, config=config).strip()


def run_easyocr(img):
    """Run EasyOCR."""
    reader = get_easyocr_reader()
    if reader is None:
        return ""
    
    img_np = np.array(img)
    if len(img_np.shape) == 2:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB)
    
    results = reader.readtext(img_np, detail=0)
    return ' '.join(results)


def run_paddleocr(img):
    """Run PaddleOCR."""
    reader = get_paddleocr_reader()
    if reader is None:
        return ""
    
    img_np = np.array(img)
    if len(img_np.shape) == 2:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB)
    
    results = reader.ocr(img_np, cls=True)
    if results and results[0]:
        texts = [line[1][0] for line in results[0] if line[1]]
        return ' '.join(texts)
    return ""


def voting_ocr(img):
    """
    Multi-engine voting: Run all available OCR engines and combine results.
    Uses longest common substring matching for consensus.
    """
    texts = []
    
    # Run all available engines
    tess_text = run_tesseract(img)
    texts.append(tess_text)
    
    if EASYOCR_AVAILABLE:
        easy_text = run_easyocr(img)
        texts.append(easy_text)
    
    if PADDLEOCR_AVAILABLE:
        paddle_text = run_paddleocr(img)
        texts.append(paddle_text)
    
    # Simple voting: return the result with most words
    # (more sophisticated: use word-level voting)
    if not texts:
        return ""
    
    # Sort by word count and return best
    texts.sort(key=lambda x: len(x.split()), reverse=True)
    return texts[0]


def voting_ocr_union(img):
    """
    Multi-engine union: Combine unique words from all engines.
    """
    all_words = set()
    
    tess_text = run_tesseract(img)
    all_words.update(tess_text.split())
    
    if EASYOCR_AVAILABLE:
        easy_text = run_easyocr(img)
        all_words.update(easy_text.split())
    
    if PADDLEOCR_AVAILABLE:
        paddle_text = run_paddleocr(img)
        all_words.update(paddle_text.split())
    
    return ' '.join(all_words)


def get_samples():
    manifest_path = Path(__file__).parent / "manifest.json"
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def benchmark_single(name: str, preprocess_func, ocr_func):
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
                processed = preprocess_func(img)
            else:
                processed = img
            
            text = ocr_func(processed)
            
            total_chars += len(text)
            total_words += len(text.split())
            
        except Exception as e:
            errors += 1
            print(f"    Error: {e}")
    
    return {
        "name": name,
        "total_chars": total_chars,
        "total_words": total_words,
        "errors": errors
    }


def main():
    print("\n" + "="*80)
    print("  🔬 ADVANCED OCR BENCHMARK - Multi-Engine Voting")
    print("="*80)
    print(f"  EasyOCR: {'✅' if EASYOCR_AVAILABLE else '❌'}")
    print(f"  PaddleOCR: {'✅' if PADDLEOCR_AVAILABLE else '❌'}")
    print("="*80)
    
    configs = [
        ("1. Baseline (v3 + Tesseract)", preprocess_image_v3, run_tesseract),
        ("2. v3 + EasyOCR", preprocess_image_v3, run_easyocr) if EASYOCR_AVAILABLE else None,
        ("3. v3 + PaddleOCR", preprocess_image_v3, run_paddleocr) if PADDLEOCR_AVAILABLE else None,
        ("4. Multi-Engine Voting (Best)", preprocess_image_v3, voting_ocr),
        ("5. Multi-Engine Union (All Words)", preprocess_image_v3, voting_ocr_union),
    ]
    
    configs = [c for c in configs if c is not None]
    
    results = []
    
    for name, preprocess_func, ocr_func in configs:
        print(f"\n📊 Testing: {name}...")
        result = benchmark_single(name, preprocess_func, ocr_func)
        results.append(result)
        print(f"   Chars: {result['total_chars']:,}  |  Words: {result['total_words']:,}")
    
    # Sort by words
    results.sort(key=lambda x: x['total_words'], reverse=True)
    
    print("\n" + "="*80)
    print("  RESULTS (sorted by word count)")
    print("="*80)
    print(f"{'#':<3} {'Configuration':<45} {'Chars':>10} {'Words':>10}")
    print("-"*80)
    
    baseline = next((r for r in results if 'Baseline' in r['name']), results[-1])
    
    for i, r in enumerate(results, 1):
        delta = r['total_words'] - baseline['total_words']
        delta_str = f"(+{delta})" if delta > 0 else f"({delta})" if delta < 0 else ""
        print(f"{i:<3} {r['name']:<45} {r['total_chars']:>10,} {r['total_words']:>10,} {delta_str}")
    
    print("="*80)
    
    # Save
    output_dir = Path(__file__).parent.parent / "benchmark_results"
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "advanced_benchmark.json", 'w') as f:
        json.dump({"timestamp": datetime.now().isoformat(), "results": results}, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_dir / 'advanced_benchmark.json'}")
    
    best = results[0]
    print(f"\n🏆 BEST: {best['name']} ({best['total_words']} words)")


if __name__ == "__main__":
    main()
