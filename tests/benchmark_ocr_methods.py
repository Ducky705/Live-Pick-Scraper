# tests/benchmark_ocr_methods.py
"""
OCR Benchmark Script - Compare baseline vs improved preprocessing.
"""

import sys
import os
import json
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import pytesseract

# Load baseline OCR handler
from src.ocr_handler import extract_text, preprocess_image, TESSERACT_BIN

# Ensure Tesseract is configured
if os.path.exists(TESSERACT_BIN):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_BIN


def get_samples():
    """Get all sample images from manifest."""
    manifest_path = Path(__file__).parent / "manifest.json"
    with open(manifest_path, 'r', encoding='utf-8') as f:
        cases = json.load(f)
    return cases


def run_ocr_on_image(image_path: Path, use_improved: bool = False, save_debug: bool = False) -> dict:
    """
    Run OCR on a single image.
    Returns dict with text length, character count, and sample text.
    """
    if not image_path.exists():
        return {"error": f"File not found: {image_path}", "text_len": 0, "text": ""}
    
    try:
        if use_improved:
            # For improved, we want to see the v2 preprocessing
            from src.ocr_handler import preprocess_image_v2, extract_text_v2
            img = Image.open(image_path)
            processed_img = preprocess_image_v2(img)
            
            if save_debug:
                debug_dir = Path(__file__).parent.parent / "benchmark_results" / "debug_images"
                debug_dir.mkdir(parents=True, exist_ok=True)
                # Save as v2_filename.png
                save_path = debug_dir / f"v2_{image_path.name.split('.')[0]}.png"
                processed_img.save(save_path)
            
            # Use extract_text_v2 which uses the same preprocessing but adds retry logic
            text = extract_text_v2(str(image_path))
        else:
            # Baseline: use original pipeline
            img = Image.open(image_path)
            processed_img = preprocess_image(img)
            
            if save_debug:
                debug_dir = Path(__file__).parent.parent / "benchmark_results" / "debug_images"
                debug_dir.mkdir(parents=True, exist_ok=True)
                # Save as v1_filename.png
                save_path = debug_dir / f"v1_{image_path.name.split('.')[0]}.png"
                processed_img.save(save_path)
            
            config = '--psm 6 --oem 3'
            text = pytesseract.image_to_string(processed_img, config=config).strip()
        
        return {
            "text_len": len(text),
            "word_count": len(text.split()),
            "text": text[:200] + "..." if len(text) > 200 else text
        }
    except Exception as e:
        return {"error": str(e), "text_len": 0, "text": ""}


def run_benchmark(use_improved: bool = False):
    """Run OCR benchmark on all samples."""
    cases = get_samples()
    results = []
    
    base_dir = Path(__file__).parent.parent
    
    for case in cases:
        image_file = case.get("image_file", "")
        if not image_file:
            continue
        
        image_path = base_dir / "tests" / image_file
        # Pass save_debug=True here
        result = run_ocr_on_image(image_path, use_improved, save_debug=True)
        result["case_id"] = case.get("id", "unknown")
        result["expected_picks"] = len(case.get("expected_picks", []))
        results.append(result)
    
    return results


def print_summary(results: list, label: str):
    """Print summary statistics."""
    total_text_len = sum(r.get("text_len", 0) for r in results)
    total_words = sum(r.get("word_count", 0) for r in results)
    errors = sum(1 for r in results if "error" in r)
    
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Total Samples:     {len(results)}")
    print(f"  Total Characters:  {total_text_len}")
    print(f"  Total Words:       {total_words}")
    print(f"  Errors:            {errors}")
    print(f"  Avg Chars/Image:   {total_text_len / len(results):.1f}")
    print(f"{'='*60}\n")
    
    return {
        "label": label,
        "samples": len(results),
        "total_chars": total_text_len,
        "total_words": total_words,
        "errors": errors,
        "avg_chars": total_text_len / len(results) if results else 0
    }


def main():
    print("\n🔬 OCR Benchmark - Baseline vs Improved")
    print("="*60)
    
    # Save baseline results
    output_dir = Path(__file__).parent.parent / "benchmark_results"
    output_dir.mkdir(exist_ok=True)
    
    # Run Baseline
    print("\n📊 Running BASELINE (current preprocessing)...")
    baseline_results = run_benchmark(use_improved=False)
    baseline_summary = print_summary(baseline_results, "BASELINE (Current)")
    
    with open(output_dir / "ocr_baseline.json", 'w') as f:
        json.dump({
            "summary": baseline_summary,
            "results": baseline_results
        }, f, indent=2)
    
    # Run Improved
    print("\n📊 Running IMPROVED (v2 preprocessing)...")
    improved_results = run_benchmark(use_improved=True)
    improved_summary = print_summary(improved_results, "IMPROVED (v2)")
    
    with open(output_dir / "ocr_improved.json", 'w') as f:
        json.dump({
            "summary": improved_summary,
            "results": improved_results
        }, f, indent=2)
    
    # Comparison
    print("\n" + "="*60)
    print("  COMPARISON")
    print("="*60)
    
    baseline_chars = baseline_summary["total_chars"]
    improved_chars = improved_summary["total_chars"]
    diff_chars = improved_chars - baseline_chars
    pct_change = ((improved_chars - baseline_chars) / baseline_chars * 100) if baseline_chars else 0
    
    print(f"  Baseline Total Chars:  {baseline_chars}")
    print(f"  Improved Total Chars:  {improved_chars}")
    print(f"  Difference:            {diff_chars:+d} chars ({pct_change:+.1f}%)")
    print()
    
    baseline_words = baseline_summary["total_words"]
    improved_words = improved_summary["total_words"]
    diff_words = improved_words - baseline_words
    pct_words = ((improved_words - baseline_words) / baseline_words * 100) if baseline_words else 0
    
    print(f"  Baseline Total Words:  {baseline_words}")
    print(f"  Improved Total Words:  {improved_words}")
    print(f"  Difference:            {diff_words:+d} words ({pct_words:+.1f}%)")
    print("="*60)
    
    if diff_chars > 0:
        print("  ✅ IMPROVED preprocessing extracted MORE text!")
    elif diff_chars < 0:
        print("  ⚠️  IMPROVED preprocessing extracted LESS text (may need tuning)")
    else:
        print("  ➖ No difference in character count")
    
    print(f"\n✅ Results saved to: {output_dir}")


if __name__ == "__main__":
    main()
