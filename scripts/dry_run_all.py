import json
import os
import sys
import logging
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.extraction_pipeline import ExtractionPipeline
from src.config import OUTPUT_DIR, DATA_DIR

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("DryRun")

def load_data():
    source_file = os.path.join(OUTPUT_DIR, "debug_msgs.json")
    if not os.path.exists(source_file):
        logger.error(f"Source file not found: {source_file}")
        return []
    
    with open(source_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Filter for selected messages only
    # US-001: The user wants to run on "REAL picks", so we assume "selected=True" 
    # implies messages that were flagged as potentially relevant by the scraper.
    selected_msgs = [m for m in data if m.get("selected")]
    return selected_msgs

def driver():
    logger.info("Starting Dry Run Verification...")
    
    messages = load_data()
    logger.info(f"Loaded {len(messages)} selected messages for dry run.")
    
    if not messages:
        logger.warning("No messages to process. Exiting.")
        return

    # Set a fixed target date for consistency with the dataset
    # The dataset seems to be around Feb 14-15 2026 based on previous file reads
    target_date = "2026-02-14" 
    
    logger.info(f"Running ExtractionPipeline for date: {target_date}")
    
    # Run Pipeline
    # Strategy 'groq' is faster and cheaper for dry runs if available
    picks = ExtractionPipeline.run(
        messages, 
        target_date=target_date, 
        batch_size=20, 
        strategy="groq"
    )
    
    logger.info(f"Dry Run Complete. Total Picks Extracted: {len(picks)}")
    logger.info(f"Check {OUTPUT_DIR}/verification_report_{target_date}.md for details.")

if __name__ == "__main__":
    driver()
