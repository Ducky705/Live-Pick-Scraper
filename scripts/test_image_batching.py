
import sys
import os
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.openrouter_client import openrouter_completion

MODELS_TO_TEST = [
    "qwen/qwen-2-vl-7b-instruct:free"
]

BATCH_SIZES = [1, 3, 5, 10]

def get_test_image():
    # Find a jpg in tests/
    base = Path(__file__).parent.parent
    for root, _, files in os.walk(base / "tests"):
        for f in files:
            if f.endswith(".jpg"):
                return str(Path(root) / f)
    return None

def run_test():
    img_path = get_test_image()
    if not img_path:
        print("❌ No test image found!")
        return

    print(f"📸 Using test image: {img_path}")
    
    for model in MODELS_TO_TEST:
        print(f"\n🔬 Testing Model: {model}")
        
        for count in BATCH_SIZES:
            print(f"   Testing {count} images...", end="", flush=True)
            
            images = [img_path] * count
            prompt = f"Describe these {count} images briefly. Are they all the same?"
            
            try:
                start = time.time()
                # We expect the client to handle list of images
                response = openrouter_completion(prompt, model=model, images=images, timeout=60)
                elapsed = time.time() - start
                
                print(f" ✅ Success ({elapsed:.1f}s)")
                # print(f"      Response: {response[:50]}...")
            except Exception as e:
                print(f" ❌ Failed: {str(e)}")

if __name__ == "__main__":
    run_test()
