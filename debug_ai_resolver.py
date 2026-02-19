
import logging
import sys
import os

# Setup path
sys.path.insert(0, os.path.abspath("."))

# Configure logging
logging.basicConfig(level=logging.INFO)

from src.grading.ai_resolver import AIResolver

def test():
    # Test cases that should trigger AI
    picks = [
        ("Warriors -5 Suns ML", "NBA"),
    ]
    
    print("Testing AI Resolver Direct...")
    
    for text, league in picks:
        print(f"\n--- Testing: '{text}' ---")
        try:
            result = AIResolver.parse_pick(text, league)
            if result:
                print(f"SUCCESS: {result}")
            else:
                print("FAILURE: Returned None")
        except Exception as e:
            print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test()
