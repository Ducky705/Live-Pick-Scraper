
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ocr_handler import extract_text
print("Testing extract_text (AI)...")
# Use a sample image from tests if available, otherwise just check function
# We can't really test without an image path that exists.
# Let's try to find one.
import os
for root, dirs, files in os.walk("tests"):
    for file in files:
        if file.endswith(".jpg"):
            path = os.path.join(root, file)
            print(f"Using image: {path}")
            res = extract_text(path)
            print(f"Result: {res[:100]}...")
            sys.exit(0)
print("No test image found.")
