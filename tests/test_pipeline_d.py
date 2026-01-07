
import os
import sys
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ocr_handler import extract_text_batch_v3_ai

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_pipeline_d():
    # Use a sample image from tests/samples if available, else look for one
    sample_dir = os.path.join("tests", "samples")
    if not os.path.exists(sample_dir):
        print("No tests/samples dir")
        return

    images = [os.path.join(sample_dir, f) for f in os.listdir(sample_dir) if f.endswith(('.jpg', '.png'))][:2]
    
    if not images:
        print("No images found in tests/samples")
        return

    print(f"Testing Pipeline D (V3 + AI) on {len(images)} images: {images}")
    
    # Run Pipeline D
    results = extract_text_batch_v3_ai(images)
    
    for i, text in enumerate(results):
        print(f"\n--- Image {i+1} Result ---")
        print(text[:200] + "..." if len(text) > 200 else text)
        print("-" * 30)

if __name__ == "__main__":
    test_pipeline_d()
