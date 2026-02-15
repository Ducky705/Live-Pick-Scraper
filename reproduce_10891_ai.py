
import sys
import os
import asyncio
import logging
import json

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.parallel_batch_processor import parallel_processor
from src.prompts.decoder import normalize_response

# Setup Logging
logging.basicConfig(level=logging.DEBUG)

async def main():
    print("--- Reproducing Message 10891 (AI ONLY) ---")
    
    # Load comprehensive set
    with open(os.path.join("data", "output", "comprehensive_debug_set.json"), "r", encoding="utf-8") as f:
        all_msgs = json.load(f)
    
    # Find Message 10891
    msg = next((m for m in all_msgs if str(m.get("id")) == "10891"), None)
    if not msg:
        print("Message 10891 not found.")
        return

    print(f"Loaded Message {msg['id']}")
    
    # Run AI Batch Processing directly
    batches = [[msg]]
    print("Sending to AI...")
    
    # Use "groq" strategy (or whatever default)
    # Note: parallel_processor.process_batches returns raw response strings
    results = parallel_processor.process_batches(batches)
    
    raw_response = results[0]
    print(f"\nRaw AI Response:\n{raw_response}\n")
    
    if raw_response:
        # Normalize
        valid_ids = [str(msg['id'])]
        picks = normalize_response(raw_response, expand=True, valid_message_ids=valid_ids)
        print(f"Normalized Picks: {len(picks)}")
        for p in picks:
            print(json.dumps(p, indent=2))
    else:
        print("❌ AI returned None.")

if __name__ == "__main__":
    asyncio.run(main())
