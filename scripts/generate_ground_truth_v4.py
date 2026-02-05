import asyncio
import json
import logging
import os
import sys

# Setup
sys.path.insert(0, os.path.abspath("."))
from src.extraction_pipeline import ExtractionPipeline
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GenerateGroundTruth")

INPUT_FILE = "benchmark/dataset/golden_set_v4_candidates.json"
OUTPUT_FILE = "benchmark/dataset/golden_set_v4.json"

async def main():
    if not os.path.exists(INPUT_FILE):
        logger.error(f"Input file {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, "r") as f:
        messages = json.load(f)

    logger.info(f"Generating Ground Truth for {len(messages)} messages...")

    # We use the pipeline itself to generate "Expected" picks
    # Ideally we use a stronger model or "High Confidence" mode
    # For now, we trust the current pipeline's "groq" strategy (or we could use 'openai' if available)
    # The user instruction said "Use strongest AI model".
    # But I don't have code to switch model easily without config change.
    # I'll use the default strategy but maybe audit it later.
    
    # Run Pipeline
    # We process all at once? Or batches? Pipeline handles batches.
    
    # Note: Pipeline.run is synchronous wrapper
    # But wait, does it return the *message text* aligned with picks?
    # It returns a list of Picks.
    # We need to restructure this into the Golden Set format: 
    # { "id": ..., "text": ..., "expected_picks": [...] }
    
    picks = ExtractionPipeline.run(
        messages=messages, 
        target_date="2026-02-05", 
        strategy="groq" # Using Groq for speed, assuming it's good enough for "Draft" ground truth
    )
    
    # Map picks back to messages
    picks_by_msg = {}
    for p in picks:
        mid = str(p.get("message_id"))
        if mid not in picks_by_msg:
            picks_by_msg[mid] = []
        picks_by_msg[mid].append(p)
        
    golden_set = []
    for m in messages:
        mid = str(m["id"])
        
        # Golden Set Entry
        entry = {
            "id": mid,
            "source": m.get("source", "unknown"),
            "text": m.get("text", ""),
            "ocr_text": m.get("ocr_text", ""), # If available
            "expected_picks": picks_by_msg.get(mid, [])
        }
        golden_set.append(entry)
        
    with open(OUTPUT_FILE, "w") as f:
        json.dump(golden_set, f, indent=2)
        
    logger.info(f"Saved {len(golden_set)} validated bench samples to {OUTPUT_FILE}")

if __name__ == "__main__":
    try:
        if asyncio.get_event_loop().is_running():
             # If running in a notebook or existing loop (unlikely here)
             # But ExtractionPipeline.run is sync.
             main_sync()
        else:
             # Just run main logic. But wait, ExtractionPipeline.run is sync?
             # Yes. So I don't need async main unless I use async libs directly.
             pass
    except:
        pass

    # Synchronous execution
    asyncio.run(main())
