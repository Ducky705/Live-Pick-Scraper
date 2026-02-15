
import sys
import os
import asyncio
import logging
import json

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.extraction_pipeline import ExtractionPipeline

# Setup Logging
logging.basicConfig(level=logging.DEBUG)

async def main():
    print("--- Reproducing Message 10891 Failure ---")
    
    # Load comprehensive set
    with open(os.path.join("data", "output", "comprehensive_debug_set.json"), "r", encoding="utf-8") as f:
        all_msgs = json.load(f)
    
    # Find Message 10891
    msg = next((m for m in all_msgs if str(m.get("id")) == "10891"), None)
    if not msg:
        print("Message 10891 not found in comprehensive_debug_set.json")
        return

    print(f"Loaded Message {msg['id']}")
    
    print(f"Running extraction on Message {msg['id']}...")
    
    # Force AI usage by bypassing any cache (if it exists)
    # We pass a non-existent cache path to ensure fresh run
    picks = ExtractionPipeline.run([msg], "2026-01-24", extraction_cache_path="non_existent_cache.json")
    
    print(f"\nExtracted {len(picks)} picks:")
    for p in picks:
        print(json.dumps(p, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
