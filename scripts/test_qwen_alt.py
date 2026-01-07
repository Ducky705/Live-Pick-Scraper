
import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.openrouter_client import openrouter_completion

MODEL = "qwen/qwen-2-vl-7b-instruct:free"

def run_test():
    prompt = "Hello"
    try:
        res = openrouter_completion(prompt, model=MODEL, timeout=30)
        print(f"Model {MODEL} is VALID. Response: {res[:20]}")
    except Exception as e:
        print(f"Model {MODEL} Failed: {e}")

if __name__ == "__main__":
    run_test()
