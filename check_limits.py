import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_TOKEN")

if not api_key:
    print("Error: GEMINI_TOKEN not found in .env")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    # Check if there's any limit info in the response or just model metadata
    # We will print model names and available fields to see if limits are exposed
    
    if "models" in data:
        print(f"{'Model Name':<50} | {'Input Limit':<15} | {'Output Limit':<15}")
        print("-" * 85)
        for model in data["models"]:
            # Check for any field that looks like a rate limit
            # Common fields: name, version, displayName, description, inputTokenLimit, outputTokenLimit, supportedGenerationMethods, temperature, topP, topK
            name = model.get("name", "N/A")
            display_name = model.get("displayName", "N/A")
            input_limit = model.get("inputTokenLimit", "N/A")
            output_limit = model.get("outputTokenLimit", "N/A")
            
            # Print basic info first
            print(f"{name:<50} | {str(input_limit):<15} | {str(output_limit):<15}")
            
            # Uncomment to inspect full JSON for one model if needed
            # if "gemini-1.5-flash" in name:
            #     print(json.dumps(model, indent=2))
                
    else:
        print("No models found or unexpected response format.")
        print(json.dumps(data, indent=2))

except Exception as e:
    print(f"Error fetching models: {e}")
