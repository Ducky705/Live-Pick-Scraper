import sys
import os

# Add root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

from src.ocr_handler import extract_text
from config import BASE_DIR

def test_ocr(rel_path):
    print(f"Testing OCR on: {rel_path}")
    full_path = os.path.join(BASE_DIR, rel_path)
    print(f"Full Path: {full_path}")
    
    if not os.path.exists(full_path):
        print("ERROR: File does not exist")
        return
        
    try:
        text = extract_text(rel_path)
        print("--- OCR OUTPUT START ---")
        print(repr(text))
        print("--- OCR OUTPUT END ---")
        print(f"Length: {len(text)}")
    except Exception as e:
        print(f"OCR Exception: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_ocr(sys.argv[1])
    else:
        print("Usage: python tests/debug_ocr.py <relative_path>")
