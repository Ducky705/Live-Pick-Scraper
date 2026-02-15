
import logging
import sys
import os
import json
import asyncio

# Setup Logging to console
logging.basicConfig(level=logging.INFO, format='%(name)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

from src.extraction_pipeline import ExtractionPipeline

async def main():
    print("--- Debugging Message 10891 ONLY ---")
    
    # Load 10891
    with open(os.path.join("data", "output", "comprehensive_debug_set.json"), "r", encoding="utf-8") as f:
        all_msgs = json.load(f)
    msg = next((m for m in all_msgs if str(m.get("id")) == "10891"), None)
    
    if not msg:
        print("Msg 10891 not found")
        return

    # Run Pipeline
    picks = ExtractionPipeline.run([msg], target_date="2026-02-08", strategy="groq")
    
    print(f"Final Extracted Picks: {len(picks)}")
    for p in picks:
        print(f" - {p.get('pick')}")

if __name__ == "__main__":
    asyncio.run(main())
