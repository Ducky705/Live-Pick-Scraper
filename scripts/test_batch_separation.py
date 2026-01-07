
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.openrouter_client import openrouter_completion

MODEL = "google/gemma-3-12b-it:free"
SAMPLES_DIR = Path(__file__).parent.parent / "tests" / "samples"
IMAGES = [
    str(SAMPLES_DIR / "-1001900292133_55808.jpg"),
    str(SAMPLES_DIR / "-1001900292133_55809.jpg"),
    str(SAMPLES_DIR / "-1001900292133_55810.jpg"),
    str(SAMPLES_DIR / "-1001900292133_55811.jpg"),
    str(SAMPLES_DIR / "-1001900292133_55812.jpg")
]

def run_test():
    print(f"📸 Testing batch separation with {len(IMAGES)} images using {MODEL}...")
    
    prompt = (
        f"You are receiving {len(IMAGES)} images. "
        "Extract the text from EACH image securely and separately. "
        "Return the result STRICTLY as a JSON list of strings, "
        "where index 0 corresponds to the first image, index 1 to the second, and so on. "
        "Do not include any other text or markdown formatting. "
        "Example format: [\"text from image 1\", \"text from image 2\", ...]"
    )
    
    try:
        response = openrouter_completion(prompt, model=MODEL, images=IMAGES, timeout=120)
        print("\n--- RAW RESPONSE ---")
        print(response)
        print("--- END RAW RESPONSE ---\n")
        
        # Attempt to parse
        if response.startswith("```json"):
            response = response.split("```json")[1].split("```")[0].strip()
        elif response.startswith("```"):
            response = response.split("```")[1].split("```")[0].strip()
            
        data = json.loads(response)
        
        print(f"✅ Parsed Successfully! Got {len(data)} items.")
        for i, item in enumerate(data):
            print(f"\n[Image {i}] Length: {len(item)} chars")
            print(f"Snippet: {item[:50]}...")
            
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    run_test()
