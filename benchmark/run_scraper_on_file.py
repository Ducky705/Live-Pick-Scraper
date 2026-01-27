import json
import os
import sys
import asyncio
import logging
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.extraction_pipeline import ExtractionPipeline
from src.utils import backfill_odds
from src.game_enricher import enrich_picks
from src.pick_deduplicator import deduplicate_by_capper

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ScraperRunner")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run ExtractionPipeline on a local JSON file"
    )
    parser.add_argument(
        "--input", type=str, required=True, help="Input messages JSON file"
    )
    parser.add_argument(
        "--output", type=str, required=True, help="Output picks JSON file"
    )
    args = parser.parse_args()

    input_path = args.input
    output_path = args.output

    if not os.path.exists(input_path):
        logger.error(f"Input file not found: {input_path}")
        return

    logger.info(f"Loading messages from {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle wrapped format
    if isinstance(data, dict) and "messages" in data:
        messages = data["messages"]
    elif isinstance(data, list):
        messages = data
    else:
        logger.error("Unknown input format. Expected list or {'messages': [...]}")
        return

    logger.info(f"Loaded {len(messages)} messages.")

    # Determine target date from first message or default to today
    target_date = "2026-01-24"  # Default fallback
    if messages and messages[0].get("date"):
        # Attempt to parse date from "2026-01-24 18:28 ET"
        try:
            target_date = messages[0]["date"].split()[0]
        except:
            pass

    logger.info(f"Target Date: {target_date}")

    # Run Pipeline
    logger.info("Running ExtractionPipeline...")
    picks = ExtractionPipeline.run(messages, target_date)

    logger.info(f"Pipeline complete. Extracted {len(picks)} picks.")

    # Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved picks to {output_path}")


if __name__ == "__main__":
    main()
