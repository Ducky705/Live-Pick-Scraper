"""
Debug Thinking Models
=====================
Sends a single batch to GPT-OSS 120B to inspect the RAW output.
Checks for <think> tags or formatting issues causing 0% recall.
"""

import json
import os
import sys
import logging
from src.openrouter_client import openrouter_completion

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    # Load 5 messages from Golden Set
    with open(r"benchmark\dataset\ocr_golden_set.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    messages = []
    for k, v in list(data.items())[:5]:
        messages.append(f"Message ID {k}: {v}")
        
    prompt = f"""
    Extract betting picks from these messages. Return ONLY a JSON list of objects.
    
    Messages:
    {json.dumps(messages, indent=2)}
    
    Format:
    [
      {{
        "selection": "Team Name",
        "line": -5.5
      }}
    ]
    """
    
    model = "openai/gpt-oss-120b:free"
    
    # DISABLE FALLBACKS
    import src.openrouter_client as client_module
    raw_defaults = list(client_module.DEFAULT_MODELS)
    client_module.DEFAULT_MODELS = []
    
    print(f"Sending prompt to {model}...")
    try:
        raw_output = openrouter_completion(prompt, model=model, timeout=120)
        
        # RESTORE
        client_module.DEFAULT_MODELS = raw_defaults
        print("\n" + "="*40)
        print("RAW OUTPUT START")
        print("="*40)
        print(raw_output)
        print("="*40)
        print("RAW OUTPUT END")
        print("="*40)
        
        if "<think>" in raw_output:
            print("\n[!] DETECTED <think> TAGS! Parser likely needs update.")
        else:
            print("\n[ok] No <think> tags detected.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
