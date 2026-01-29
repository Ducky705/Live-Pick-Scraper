import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_TOKEN")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash?key={api_key}"

try:
    response = requests.get(url)
    # We won't raise for status immediately to see error body if it fails
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(e)
