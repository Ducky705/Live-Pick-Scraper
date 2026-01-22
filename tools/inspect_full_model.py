import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_TOKEN")
# Using a model name that definitely exists from the previous list
model_name = "models/gemini-2.0-flash" 
url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}?key={api_key}"

try:
    response = requests.get(url)
    data = response.json()
    print(json.dumps(data, indent=2))
except Exception as e:
    print(e)
