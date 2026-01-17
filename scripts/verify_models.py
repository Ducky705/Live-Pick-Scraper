
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("Error: OPENROUTER_API_KEY not found.")
    exit(1)

def check_models():
    print("Fetching OpenRouter model list...")
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"Error: API returned {response.status_code}")
            print(response.text)
            return

        data = response.json()
        models = data.get('data', [])
        
        # Check for specific models
        targets = [
            "tngtech/deepseek-r1t2-chimera:free",
            "google/gemini-2.0-pro-exp-02-05:free",
            "google/gemini-2.0-flash-exp:free",
            "deepseek/deepseek-r1-distill-llama-70b:free"
        ]
        
        print(f"\nScanning {len(models)} available models for targets:")
        
        found = {t: False for t in targets}
        
        for m in models:
            mid = m.get('id')
            if mid in targets:
                found[mid] = True
                print(f"[FOUND] {mid}")
            
        print("\nMissing Models:")
        for t, was_found in found.items():
            if not was_found:
                print(f"[MISSING] {t}")
                
        # List all google free models to find the right pro one
        print("\nAvailable 'google' + 'free' models:")
        for m in models:
            mid = m.get('id', '')
            if 'google' in mid and 'free' in mid:
                print(f" - {mid}")

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    check_models()
