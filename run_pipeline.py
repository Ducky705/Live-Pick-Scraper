# File: ./run_pipeline.py
import asyncio
import logging
from datetime import datetime

# --- Local Imports ---
from config import EASTERN_TIMEZONE, OPERATIONAL_START_HOUR_ET, OPERATIONAL_END_HOUR_ET
from scrapers import run_scrapers
from processing_service import run_processor

def is_within_operational_hours() -> bool:
    """Checks if the current time is within the configured operational window."""
    now_et = datetime.now(EASTERN_TIMEZONE)
    hour = now_et.hour
    
    if OPERATIONAL_START_HOUR_ET <= hour < OPERATIONAL_END_HOUR_ET:
        logging.info(f"Current time {now_et.strftime('%H:%M:%S %Z')} is within the operational window.")
        return True
    else:
        logging.info(f"Current time {now_et.strftime('%H:%M:%S %Z')} is outside the operational window. Skipping run.")
        return False

async def main():
    """Main function for the scraping and processing pipeline."""
    if not is_within_operational_hours():
        return

    logging.info("="*20 + " STARTING SCRAPE & PROCESS RUN " + "="*20)
    try:
        logging.info("\n--- Step 1: Running Scrapers ---")
        await run_scrapers()

        logging.info("\n--- Step 2: Running AI Processing Service ---")
        run_processor()

    except Exception as e:
        logging.error(f"A critical error occurred in the pipeline: {e}", exc_info=True)
    finally:
        logging.info("="*20 + " SCRAPE & PROCESS RUN FINISHED " + "="*20)

if __name__ == "__main__":
    asyncio.run(main())