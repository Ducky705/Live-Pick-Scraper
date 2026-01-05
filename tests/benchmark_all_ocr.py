# tests/benchmark_all_ocr.py
"""
Comprehensive OCR Benchmark - Tests multiple preprocessing variants.
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import pytesseract

from src.ocr_handler import (
    preprocess_image, 
    preprocess_image_v2, 
    preprocess_image_v3,
    TESSERACT_BIN
)

if os.path.exists(TESSERACT_BIN):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_BIN


def get_samples():
    manifest_path = Path(__file__).parent / "manifest.json"
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_ocr(image_path: Path, preprocess_func, **kwargs) -> dict:
    """Run OCR with a specific preprocessing function."""
    if not image_path.exists():
        return {"error": f"File not found", "text_len": 0, "word_count": 0}
    
    try:
        img = Image.open(image_path)
        processed = preprocess_func(img, **kwargs) if kwargs else preprocess_func(img)
        
        config = '--psm 6 --oem 3'
        text = pytesseract.image_to_string(processed, config=config).strip()
        
        return {
            "text_len": len(text),
            "word_count": len(text.split()),
        }
    except Exception as e:
        return {"error": str(e), "text_len": 0, "word_count": 0}


def benchmark_variant(name: str, preprocess_func, **kwargs) -> dict:
    """Benchmark a single preprocessing variant."""
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
        result = run_ocr(image_path, preprocess_func, **kwargs)
        
        if "error" in result:
            errors += 1
        total_chars += result.get("text_len", 0)
        total_words += result.get("word_count", 0)
    
    return {
        "name": name,
        "total_chars": total_chars,
        "total_words": total_words,
        "errors": errors,
        "samples": len(cases)
    }


def main():
    print("\n" + "="*70)
    print("  🔬 COMPREHENSIVE OCR BENCHMARK")
    print("="*70)
    
    # Define all variants to test
    variants = [
        ("Baseline (v1)", preprocess_image, {}),
        ("V2 (Lanczos+Pad+Gamma+Bilateral)", preprocess_image_v2, {}),
        ("V3 Full (Deskew+Sharpen+NLM)", preprocess_image_v3, {"use_deskew": True, "use_sharpen": True, "use_nlm_denoise": True}),
        ("V3 Sharpen Only", preprocess_image_v3, {"use_deskew": False, "use_sharpen": True, "use_nlm_denoise": False}),
        ("V3 NLM Only", preprocess_image_v3, {"use_deskew": False, "use_sharpen": False, "use_nlm_denoise": True}),
        ("V3 Deskew Only", preprocess_image_v3, {"use_deskew": True, "use_sharpen": False, "use_nlm_denoise": False}),
        ("V3 Sharpen+NLM (no deskew)", preprocess_image_v3, {"use_deskew": False, "use_sharpen": True, "use_nlm_denoise": True}),
    ]
    
    results = []
    
    for name, func, kwargs in variants:
        print(f"\n📊 Testing: {name}...")
        result = benchmark_variant(name, func, **kwargs)
        results.append(result)
        print(f"   Chars: {result['total_chars']:,}  |  Words: {result['total_words']:,}")
    
    # Sort by total words (our quality metric)
    results.sort(key=lambda x: x['total_words'], reverse=True)
    
    # Print comparison table
    print("\n" + "="*70)
    print("  RESULTS (sorted by word count)")
    print("="*70)
    print(f"{'Variant':<40} {'Chars':>10} {'Words':>10} {'Δ Words':>10}")
    print("-"*70)
    
    baseline_words = next((r['total_words'] for r in results if 'Baseline' in r['name']), 0)
    
    for r in results:
        delta = r['total_words'] - baseline_words
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        print(f"{r['name']:<40} {r['total_chars']:>10,} {r['total_words']:>10,} {delta_str:>10}")
    
    print("="*70)
    
    # Save results
    output_dir = Path(__file__).parent.parent / "benchmark_results"
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "ocr_all_variants.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_dir / 'ocr_all_variants.json'}")
    
    # Identify best
    best = results[0]
    print(f"\n🏆 BEST VARIANT: {best['name']}")
    print(f"   Words: {best['total_words']} (+{best['total_words'] - baseline_words} vs baseline)")


if __name__ == "__main__":
    main()
