import sys
import os
import time
import logging
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.getcwd())

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("Probe")

# Import Clients
try:
    from src.groq_client import groq_text_completion
    from src.mistral_client import mistral_completion
    from src.cerebras_client import cerebras_completion
    from src.gemini_client import gemini_text_completion
    from src.openrouter_client import openrouter_completion
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

PROVIDERS = [
    ("groq", groq_text_completion, "llama-3.3-70b-versatile"),
    ("mistral", mistral_completion, "open-mistral-nemo"),
    ("cerebras", cerebras_completion, "llama3.1-8b"),
    ("gemini", gemini_text_completion, "gemini-2.0-flash"),
    ("openrouter", openrouter_completion, "meta-llama/llama-3.3-70b-instruct:free"),
]

PROMPT = "Ping. Reply with 'Pong'."

print("=== PROBING ALL PROVIDERS ===")

results = []

for name, func, model in PROVIDERS:
    print(f"\nTesting Provider: {name.upper()}")
    print(f"Model: {model}")
    
    try:
        start = time.time()
        # Call the function. Note: signatures might vary slightly, but usually take prompt+model.
        if name == "openrouter":
             response = func(PROMPT, model=model, timeout=30)
        else:
             response = func(PROMPT, model=model) # Helper functions usually handle timeout internally or use default
             
        duration = time.time() - start
        
        if response and len(response) > 0:
            print(f"✅ SUCCESS ({duration:.2f}s)")
            print(f"Response: {response[:50]}...")
            results.append((name, "OK", duration))
        else:
            print(f"❌ FAILED: Empty response")
            results.append((name, "EMPTY", duration))

    except Exception as e:
        print(f"❌ ERROR: {e}")
        results.append((name, f"ERROR: {str(e)[:50]}", 0))
        
    time.sleep(1)

print("\n=== FINAL REPORT ===")
print(f"{'Provider':<12} | {'Status':<10} | {'Latency':<10}")
print("-" * 40)
for name, status, duration in results:
    print(f"{name:<12} | {status:<10} | {duration:.2f}s")
