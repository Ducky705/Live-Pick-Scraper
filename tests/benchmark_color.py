# tests/benchmark_color.py
"""
Color Contrast Experiments for OCR Improvement.
Tests various color space transformations and channel extractions.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import pytesseract
import cv2
import numpy as np

from src.ocr_handler import TESSERACT_BIN

if os.path.exists(TESSERACT_BIN):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_BIN


def base_preprocess(cv_img):
    """Apply base preprocessing (upscale, padding) to any grayscale image."""
    # Upscale
    min_width = 1600
    if cv_img.shape[1] < min_width:
        scale = min_width / cv_img.shape[1]
        cv_img = cv2.resize(cv_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    
    # Padding
    pad = 50
    cv_img = cv2.copyMakeBorder(cv_img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)
    
    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cv_img = clahe.apply(cv_img)
    
    # Otsu threshold
    _, binary = cv2.threshold(cv_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Invert if dark background
    if np.sum(binary == 255) / binary.size < 0.3:
        binary = cv2.bitwise_not(binary)
    
    return binary


def preprocess_standard_gray(img):
    """Standard grayscale conversion (baseline)."""
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    return Image.fromarray(base_preprocess(gray))


def preprocess_red_channel(img):
    """Extract only the RED channel."""
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    red = cv_img[:, :, 2]  # BGR format, so index 2 is red
    return Image.fromarray(base_preprocess(red))


def preprocess_green_channel(img):
    """Extract only the GREEN channel."""
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    green = cv_img[:, :, 1]
    return Image.fromarray(base_preprocess(green))


def preprocess_blue_channel(img):
    """Extract only the BLUE channel."""
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    blue = cv_img[:, :, 0]
    return Image.fromarray(base_preprocess(blue))


def preprocess_lab_l(img):
    """Extract L channel from LAB color space (perceptual lightness)."""
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    lab = cv2.cvtColor(cv_img, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0]
    return Image.fromarray(base_preprocess(l_channel))


def preprocess_hsv_v(img):
    """Extract V (Value) channel from HSV color space."""
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
    v_channel = hsv[:, :, 2]
    return Image.fromarray(base_preprocess(v_channel))


def preprocess_ycrcb_y(img):
    """Extract Y (Luma) channel from YCrCb color space."""
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    ycrcb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2YCrCb)
    y_channel = ycrcb[:, :, 0]
    return Image.fromarray(base_preprocess(y_channel))


def preprocess_inverted(img):
    """Invert colors before grayscale conversion (for dark backgrounds)."""
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    inverted = cv2.bitwise_not(cv_img)
    gray = cv2.cvtColor(inverted, cv2.COLOR_BGR2GRAY)
    return Image.fromarray(base_preprocess(gray))


def preprocess_high_contrast(img):
    """Apply high contrast enhancement before grayscale."""
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    # Increase contrast using convertScaleAbs
    alpha = 2.0  # Contrast control (1.0-3.0)
    beta = -50   # Brightness control (-100 to 100)
    contrast = cv2.convertScaleAbs(cv_img, alpha=alpha, beta=beta)
    
    gray = cv2.cvtColor(contrast, cv2.COLOR_BGR2GRAY)
    return Image.fromarray(base_preprocess(gray))


def preprocess_max_channel(img):
    """Use the maximum of all channels for each pixel."""
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    max_channel = np.max(cv_img, axis=2)
    return Image.fromarray(base_preprocess(max_channel))


def preprocess_min_channel(img):
    """Use the minimum of all channels for each pixel."""
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    min_channel = np.min(cv_img, axis=2)
    return Image.fromarray(base_preprocess(min_channel))


def preprocess_saturation_boost(img):
    """Boost saturation before grayscale conversion."""
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
    
    # Boost saturation
    hsv[:, :, 1] = cv2.add(hsv[:, :, 1], 50)
    
    boosted = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    gray = cv2.cvtColor(boosted, cv2.COLOR_BGR2GRAY)
    return Image.fromarray(base_preprocess(gray))


def get_samples():
    manifest_path = Path(__file__).parent / "manifest.json"
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def benchmark_single(name: str, preprocess_func):
    """Benchmark a single color configuration."""
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
            img = Image.open(image_path).convert('RGB')
            processed = preprocess_func(img)
            
            config = '--psm 6 --oem 3'
            text = pytesseract.image_to_string(processed, config=config).strip()
            
            total_chars += len(text)
            total_words += len(text.split())
            
        except Exception as e:
            errors += 1
    
    return {
        "name": name,
        "total_chars": total_chars,
        "total_words": total_words,
        "errors": errors
    }


def main():
    print("\n" + "="*80)
    print("  🎨 COLOR CONTRAST EXPERIMENTS FOR OCR")
    print("="*80)
    
    configs = [
        ("1. Standard Grayscale (baseline)", preprocess_standard_gray),
        ("2. Red Channel Only", preprocess_red_channel),
        ("3. Green Channel Only", preprocess_green_channel),
        ("4. Blue Channel Only", preprocess_blue_channel),
        ("5. LAB L-Channel (Perceptual)", preprocess_lab_l),
        ("6. HSV V-Channel (Value)", preprocess_hsv_v),
        ("7. YCrCb Y-Channel (Luma)", preprocess_ycrcb_y),
        ("8. Inverted Colors", preprocess_inverted),
        ("9. High Contrast (2x)", preprocess_high_contrast),
        ("10. Max of RGB Channels", preprocess_max_channel),
        ("11. Min of RGB Channels", preprocess_min_channel),
        ("12. Saturation Boost", preprocess_saturation_boost),
    ]
    
    results = []
    
    for name, func in configs:
        print(f"\n📊 Testing: {name}...")
        result = benchmark_single(name, func)
        results.append(result)
        print(f"   Chars: {result['total_chars']:,}  |  Words: {result['total_words']:,}")
    
    # Sort by words
    results.sort(key=lambda x: x['total_words'], reverse=True)
    
    print("\n" + "="*80)
    print("  RESULTS (sorted by word count)")
    print("="*80)
    print(f"{'#':<3} {'Configuration':<40} {'Chars':>10} {'Words':>10}")
    print("-"*80)
    
    baseline = next((r for r in results if 'baseline' in r['name'].lower()), results[-1])
    
    for i, r in enumerate(results, 1):
        delta = r['total_words'] - baseline['total_words']
        delta_str = f"(+{delta})" if delta > 0 else f"({delta})" if delta < 0 else ""
        print(f"{i:<3} {r['name']:<40} {r['total_chars']:>10,} {r['total_words']:>10,} {delta_str}")
    
    print("="*80)
    
    # Save
    output_dir = Path(__file__).parent.parent / "benchmark_results"
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "color_benchmark.json", 'w') as f:
        json.dump({"timestamp": datetime.now().isoformat(), "results": results}, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_dir / 'color_benchmark.json'}")
    
    best = results[0]
    print(f"\n🏆 BEST: {best['name']} ({best['total_words']} words)")


if __name__ == "__main__":
    main()
