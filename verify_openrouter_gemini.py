import sys
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
model = "meta-llama/llama-3.3-70b-instruct:free"

print(f"Testing Model: {model}")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://test.local",
    "X-Title": "Test",
}

payload = {
    "model": model,
    "messages": [{"role": "user", "content": "Hello, are you working?"}],
    "temperature": 0.1,
}

try:
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
