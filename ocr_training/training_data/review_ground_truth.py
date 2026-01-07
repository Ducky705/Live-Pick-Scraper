# training_data/review_ground_truth.py
"""
Helper script to review and edit ground truth files.
Opens each image alongside its current OCR text for easy correction.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import json


def review_files():
    """Print each ground truth file with its image path for review."""
    
    gt_dir = Path(__file__).parent / "ground_truth"
    images_dir = Path(__file__).parent / "images"
    samples_dir = Path(__file__).parent.parent / "tests" / "samples"
    
    files = sorted(gt_dir.glob("*.gt.txt"))
    
    print("\n" + "="*80)
    print("  GROUND TRUTH REVIEW")
    print("  Edit the .gt.txt files to match the EXACT text in each image")
    print("="*80)
    
    for i, gt_file in enumerate(files, 1):
        base_name = gt_file.stem.replace(".gt", "")
        
        # Find original image
        orig_image = samples_dir / f"{base_name}.jpg"
        
        print(f"\n{'='*80}")
        print(f"[{i}/{len(files)}] {base_name}")
        print(f"  Original: {orig_image}")
        print(f"  GT File:  {gt_file}")
        print("-"*80)
        
        with open(gt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("CURRENT OCR TEXT:")
        print("-"*40)
        print(content)
        print("-"*40)
        print()
    
    print("\n" + "="*80)
    print("TO EDIT: Open the .gt.txt files in your editor and correct any errors")
    print(f"Location: {gt_dir}")
    print("="*80)


def show_stats():
    """Show statistics about ground truth files."""
    
    gt_dir = Path(__file__).parent / "ground_truth"
    files = sorted(gt_dir.glob("*.gt.txt"))
    
    total_words = 0
    total_chars = 0
    
    for gt_file in files:
        with open(gt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        total_words += len(content.split())
        total_chars += len(content)
    
    print(f"\n📊 Ground Truth Stats:")
    print(f"   Files: {len(files)}")
    print(f"   Total words: {total_words}")
    print(f"   Total chars: {total_chars}")
    print(f"   Avg words/file: {total_words / len(files):.1f}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        show_stats()
    else:
        review_files()
        show_stats()
