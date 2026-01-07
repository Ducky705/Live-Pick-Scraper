# training_data/benchmark_user_dict.py
"""
Benchmark OCR with and without user dictionary configuration.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import pytesseract

from src.ocr_handler import preprocess_image_v3, TESSERACT_BIN, TESSDATA_DIR

if os.path.exists(TESSERACT_BIN):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_BIN

os.environ['TESSDATA_PREFIX'] = TESSDATA_DIR


def get_samples():
    manifest_path = Path(__file__).parent.parent / "tests" / "manifest.json"
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def benchmark_config(name: str, config: str):
    """Benchmark a specific Tesseract configuration."""
    cases = get_samples()
    base_dir = Path(__file__).parent.parent
    
    total_chars = 0
    total_words = 0
    
    for case in cases:
        image_file = case.get("image_file", "")
        if not image_file:
            continue
        
        image_path = base_dir / "tests" / image_file
        if not image_path.exists():
            continue
        
        try:
            img = Image.open(image_path)
            processed = preprocess_image_v3(img)
            text = pytesseract.image_to_string(processed, config=config).strip()
            
            total_chars += len(text)
            total_words += len(text.split())
        except Exception as e:
            print(f"Error: {e}")
    
    return {"name": name, "config": config, "total_chars": total_chars, "total_words": total_words}


def main():
    print("\n" + "="*70)
    print("  📚 USER DICTIONARY BENCHMARK")
    print("="*70)
    
    configs = [
        ("Without User Dict", "--psm 6 --oem 3"),
        ("With User Dict", "--psm 6 --oem 3 --user-words eng.user-words --user-patterns eng.user-patterns"),
    ]
    
    results = []
    
    for name, config in configs:
        print(f"\n📊 Testing: {name}...")
        result = benchmark_config(name, config)
        results.append(result)
        print(f"   Chars: {result['total_chars']:,}  |  Words: {result['total_words']:,}")
    
    # Compare
    baseline = results[0]['total_words']
    with_dict = results[1]['total_words']
    delta = with_dict - baseline
    pct = (delta / baseline * 100) if baseline > 0 else 0
    
    print("\n" + "="*70)
    print(f"  RESULTS")
    print("="*70)
    print(f"  Without User Dict: {baseline} words")
    print(f"  With User Dict:    {with_dict} words")
    print(f"  Improvement:       {delta:+d} words ({pct:+.1f}%)")
    print("="*70)


if __name__ == "__main__":
    main()
