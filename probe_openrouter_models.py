import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

# Candidate "Best" Free Models
CANDIDATES = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-pro-exp-02-05:free",
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "google/gemini-2.0-flash-exp:free", # Previously 404
    "deepseek/deepseek-r1:free",
    "deepseek/deepseek-v3:free",
    "mistralai/mistral-large-2411:free",
    "nvidia/llama-3.1-nemotron-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "microsoft/phi-4:free"
]

print("=== PROBING OPENROUTER MODELS ===")
print(f"API Key present: {bool(api_key)}")

working_models = []

for model in CANDIDATES:
    print(f"\nTesting: {model}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://telegram-scraper.local",
        "X-Title": "CapperSuite Probe",
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Ping. valid json output: {'status': 'pong'}"}],
        "temperature": 0.1,
    }
    
    try:
        start = time.time()
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15 
        )
        duration = time.time() - start
        
        if response.status_code == 200:
            print(f"✅ SUCCESS ({duration:.2f}s)")
            working_models.append((model, duration))
        else:
            print(f"❌ FAILED: {response.status_code} - {response.text[:100]}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        
    # Sleep to avoid rate limits during probe
    time.sleep(2)

print("\n=== RESULTS ===")
working_models.sort(key=lambda x: x[1]) # Sort by speed
for m, d in working_models:
    print(f"- {m} ({d:.2f}s)")
