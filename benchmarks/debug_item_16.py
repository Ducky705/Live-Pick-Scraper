import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from src.grading.parser import PickParser

V4_PATH = "benchmark/dataset/golden_set_v4.json"

def debug_range():
    with open(V4_PATH, "r") as f:
        data = json.load(f)
        
    for i in range(97, 101): 
        if i >= len(data): break
        
        item = data[i]
        text = item["text"]
        print(f"\n--- Item {i} Text ---")
        print(f"{text[:100]}...")
        
        try:
            PickParser.parse(text)
            print("Parsed Successfully")
        except RecursionError:
            print(f"CRASHED: RecursionError on Item {i}")
            sys.exit(1)
        except Exception as e:
            print(f"CRASHED: {e} on Item {i}")

if __name__ == "__main__":
    debug_range()
