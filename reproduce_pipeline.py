
import sys
import os
import asyncio
import logging
import json

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.extraction_pipeline import ExtractionPipeline

# Setup Logging
# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)

async def main():
    print("--- Reproducing Extraction Pipeline (10891) ---")
    
    # Load comprehensive set
    with open(os.path.join("data", "output", "comprehensive_debug_set.json"), "r", encoding="utf-8") as f:
        all_msgs = json.load(f)
    
    # Find Message 10891
    msg1 = next((m for m in all_msgs if str(m.get("id")) == "10891"), None)
    # Find Message 12793 (Duplicate)
    msg2 = next((m for m in all_msgs if str(m.get("id")) == "12793"), None)
    
    msgs = []
    if msg1: msgs.append(msg1)
    if msg2: msgs.append(msg2)
    
    print(f"Loaded {len(msgs)} messages.")
    
    # Run Pipeline
    # Using same args as debug_parser_loop
    picks = ExtractionPipeline.run(
        msgs, 
        target_date="2026-02-08", # Date in debug_parser_loop
        strategy="groq",
        extraction_cache_path="non_existent_cache.json" # Bypass cache 
    )
    
    print(f"Extracted {len(picks)} picks total.")
    
    # Check breakdown
    by_msg = {}
    for p in picks:
        mid = str(p.get("message_id"))
        by_msg[mid] = by_msg.get(mid, 0) + 1
        
    print("Breakdown by Message ID:")
    print(json.dumps(by_msg, indent=2))
    
    if picks:
        print("Sample Pick:")
        print(json.dumps(picks[0], indent=2))

if __name__ == "__main__":
    asyncio.run(main())
