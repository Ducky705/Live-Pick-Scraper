import json
import os
import sys
import asyncio
import logging
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.extraction_pipeline import ExtractionPipeline

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("WiggumIter3")

GOLDEN_SET_PATH = os.path.join(os.path.dirname(__file__), "../new_golden_set.json")
OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "../data/output/test_wiggum_iter3.json"
)


async def run_wiggum():
    # Force ASCII for Windows console safety
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    if not os.path.exists(GOLDEN_SET_PATH):
        logger.error("No golden set found!")
        return

    with open(GOLDEN_SET_PATH, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    logger.info(f"Loaded {len(test_cases)} test cases from Golden Set.")

    # Prepare messages
    messages = []
    for case in test_cases:
        messages.append(
            {
                "id": case["id"],
                "text": case["text"],
                "images": case.get("images", []),
                "date": case["date"],
                "ocr_text": "",
                "ocr_texts": [],
                # Add dummy author/channel for reporting
                "author": "Unknown",
                "channel_name": "Unknown",
            }
        )

    # Pick a target date from the first case
    target_date = messages[0]["date"].split()[0]
    logger.info(f"Running ExtractionPipeline for target date: {target_date}")

    # RUN THE PIPELINE
    start_time = asyncio.get_event_loop().time()
    picks = ExtractionPipeline.run(messages, target_date)
    end_time = asyncio.get_event_loop().time()

    logger.info(
        f"Pipeline finished in {end_time - start_time:.2f}s. Extracted {len(picks)} picks."
    )

    # Save to output file
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2)

    logger.info(f"Saved extracted picks to {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(run_wiggum())
