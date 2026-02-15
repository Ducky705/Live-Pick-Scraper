
import json
import asyncio
import os
import sys
from datetime import datetime

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import OUTPUT_DIR
from src.extraction_pipeline import ExtractionPipeline
from src.auto_processor import auto_select_messages
from src.grader import grade_picks
from src.score_fetcher import fetch_scores_for_date

async def main():
    debug_file = os.path.join(OUTPUT_DIR, "debug_msgs.json")
    if not os.path.exists(debug_file):
        print(f"File not found: {debug_file}")
        return

    target_date = "2026-02-14"
    raw_picks_file = os.path.join(OUTPUT_DIR, f"picks_{target_date}_raw.json")
    
    if os.path.exists(raw_picks_file):
        print(f"Loading existing raw picks from {raw_picks_file}...")
        with open(raw_picks_file, "r") as f:
            picks = json.load(f)
    else:
        print(f"Loading {debug_file}...")
        with open(debug_file, "r", encoding="utf-8") as f:
            msgs = json.load(f)
        print(f"Loaded {len(msgs)} messages.")

        short_msgs = []
        for m in msgs:
            text_len = len(m.get("text", "") or "") + len(m.get("ocr_text", "") or "")
            if text_len < 30000:
                short_msgs.append(m)
            else:
                print(f"Skipping long message {m.get('id')} ({text_len} chars)")
                
        print("Running classification...")
        classified_msgs = auto_select_messages(short_msgs, use_ai=True)
        selected_msgs = [m for m in classified_msgs if m.get("selected")]
        print(f"Selected {len(selected_msgs)} picks.")

        if not selected_msgs:
            print("No picks selected.")
            return

        print(f"Extracting picks for {target_date}...")
        picks = ExtractionPipeline.run(selected_msgs, target_date)
        print(f"Extracted {len(picks)} picks.")
        
        # Save raw picks
        with open(raw_picks_file, "w") as f:
            json.dump(picks, f, indent=2)
        print(f"Saved raw picks to {raw_picks_file}")

    # Grading
    print("Fetching scores...")
    # fetch_scores_for_date is sync, run in thread
    scores = await asyncio.to_thread(fetch_scores_for_date, target_date)
    print(f"Fetched {len(scores)} scores.")
    
    print("Grading...")
    graded_picks = grade_picks(picks, scores)
    
    # Save
    outfile = os.path.join(OUTPUT_DIR, f"picks_{target_date}_manual.json")
    with open(outfile, "w") as f:
        json.dump(graded_picks, f, indent=2)
    print(f"Saved to {outfile}")

if __name__ == "__main__":
    asyncio.run(main())
