
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

url = "https://openrouter.ai/api/v1/models"
headers = {
    "Authorization": f"Bearer {api_key}",
}

print(f"Fetching models from {url}...")
try:
    response = requests.get(url, headers=headers, timeout=30)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        models = data.get('data', [])
        # Filter for models containing 'free' or just list some popular ones
        free_models = [m['id'] for m in models if 'free' in m['id'].lower()]
        print(f"Found {len(models)} models.")
        print("Free models available:")
        for m in free_models:
            print(f" - {m}")
    else:
        print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")
