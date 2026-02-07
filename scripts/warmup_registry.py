import json
import os
import sys
import time
import logging

# Ensure project root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.grading.parser import PickParser
from src.parsing.registry import TemplateRegistry
from src.parsing.fingerprinter import Fingerprinter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_json(path):
    if not os.path.exists(path):
        logging.warning(f"File not found: {path} (Skipping)")
        return []
        
    try:
        with open(path, "r") as f:
            data = json.load(f)
            
        # Normalize structure
        if isinstance(data, dict) and "messages" in data:
            return data["messages"]
        elif isinstance(data, list):
            return data
        else:
            return []
    except Exception as e:
        logging.error(f"Error loading {path}: {e}")
        return []

def warmup():
    print("--- Starting Registry Warm-Up ---")
    
    registry = TemplateRegistry()
    initial_count = len(registry.templates)
    print(f"Initial Templates: {initial_count}")
    
    # 1. Load Data
    cache_msgs = load_json("data/cache/messages.json")
    v4_msgs = load_json("benchmark/dataset/golden_set_v4.json")
    
    all_msgs = cache_msgs + v4_msgs
    print(f"Total Messages to Process: {len(all_msgs)}")
    
    learned_count = 0
    skipped_count = 0
    errors = 0
    
    # Track unique fingerprints to avoid redundant processing
    seen_fps = set()
    
    for i, msg in enumerate(all_msgs):
        text = msg.get("text", "")
        # Heuristic: Split message into lines to simulate Extractor output
        # Most picks in Telegram are line-delimited.
        lines = text.split('\n')
        
        # Only process lines that look like picks to avoid spamming AI with "Hello" or "BOOM"
        import re
        for line in lines:
            line = line.strip()
            if len(line) < 5 or len(line) > 100:
                continue
            
            # Simple heuristic: must have digits (odds/line) and letters (team)
            if not re.search(r'\d', line) or not re.search(r'[a-zA-Z]', line):
                continue
                
            fp_line = Fingerprinter.fingerprint(line)
            
            # Check Registry (Fast Path)
            if fp_line in seen_fps:
                continue
            if registry.get_template(fp_line):
                seen_fps.add(fp_line)
                continue
                
            logging.info(f"[{i+1}/{len(all_msgs)}] Learning Line: '{line[:50]}...'")
            
            try:
                # Parse triggers learning
                PickParser.parse(line)
                
                # Check if we learned it
                if registry.get_template(fp_line):
                    learned_count += 1
                    seen_fps.add(fp_line)
                    logging.info(f"-> LEARNED: {fp_line[:50]}...")
                    # Sleep to be nice to API
                    time.sleep(1.5)
                else:
                    skipped_count += 1
                    
            except Exception as e:
                logging.error(f"Error processing line: {e}")
                errors += 1
            
    final_count = len(registry.templates)
    print("\n--- Warm-Up Complete ---")
    print(f"Templates Before: {initial_count}")
    print(f"Templates After:  {final_count}")
    print(f"Net New Learned:  {final_count - initial_count}")
    print(f"Total Learned (Session): {learned_count}")
    print(f"Skipped/Failed: {skipped_count}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    warmup()
