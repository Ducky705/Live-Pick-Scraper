# training_data/create_tessdata_config.py
"""
Create custom Tesseract configuration with user words and patterns.
This provides improvement without full LSTM training.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ocr_handler import TESSDATA_DIR


def create_user_words_file():
    """Create eng.user-words file in tessdata directory."""
    
    words_src = Path(__file__).parent / "user_words.txt"
    words_dst = Path(TESSDATA_DIR) / "eng.user-words"
    
    if not words_src.exists():
        print(f"❌ Source file not found: {words_src}")
        return
    
    with open(words_src, 'r', encoding='utf-8') as f:
        words = f.read()
    
    with open(words_dst, 'w', encoding='utf-8') as f:
        f.write(words)
    
    print(f"✅ Created: {words_dst}")


def create_user_patterns_file():
    """Create eng.user-patterns file in tessdata directory."""
    
    patterns_src = Path(__file__).parent / "user_patterns.txt"
    patterns_dst = Path(TESSDATA_DIR) / "eng.user-patterns"
    
    if not patterns_src.exists():
        print(f"❌ Source file not found: {patterns_src}")
        return
    
    with open(patterns_src, 'r', encoding='utf-8') as f:
        patterns = f.read()
    
    with open(patterns_dst, 'w', encoding='utf-8') as f:
        f.write(patterns)
    
    print(f"✅ Created: {patterns_dst}")


def update_ocr_config():
    """Print the config string to use with pytesseract."""
    
    print("\n📝 Updated Tesseract configuration:")
    print("-" * 60)
    print("Add this to your pytesseract calls:")
    print()
    print('  custom_config = "--psm 6 --oem 3 --user-words eng.user-words --user-patterns eng.user-patterns"')
    print()
    print("Or update ocr_handler.py to include these options.")


if __name__ == "__main__":
    print("\n🔧 Creating Tesseract User Configuration")
    print("=" * 60)
    print(f"Tessdata directory: {TESSDATA_DIR}")
    print()
    
    create_user_words_file()
    create_user_patterns_file()
    update_ocr_config()
    
    print("\n✅ Configuration complete!")
