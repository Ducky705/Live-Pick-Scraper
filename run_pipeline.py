import asyncio
import logging
from datetime import datetime
import pytz

# Import the main functions from your existing scripts
from scrapers import run_scrapers
from processing_service import run_processor

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
EASTERN_TIMEZONE = pytz.timezone('US/Eastern')

def is_within_operational_hours() -> bool:
    """Checks if the current time is between 11 AM and 11 PM Eastern Time."""
    now_et = datetime.now(EASTERN_TIMEZONE)
    hour = now_et.hour
    
    # The operational window is from 11:00:00 ET to 22:59:59 ET.
    # *** FIX: Changed the start hour from 10 to 11 ***
    if 10 <= hour < 23:
        logging.info(f"Current time {now_et.strftime('%H:%M:%S %Z')} is within the operational window (11 AM - 11 PM ET).")
        return True
    else:
        logging.info(f"Current time {now_et.strftime('%H:%M:%S %Z')} is outside the operational window. Skipping run.")
        return False

async def main():
    """
    Main function for the scraping and processing pipeline.
    This script is designed to be run frequently by a scheduler (e.g., cron, GitHub Actions).
    """
    if not is_within_operational_hours():
        return

    logging.info("="*20 + " STARTING SCRAPE & PROCESS RUN " + "="*20)
    try:
        # Step 1: Scrape raw data from sources
        logging.info("\n--- Step 1: Running Scrapers ---")
        await run_scrapers()

        # Step 2: Process raw picks using AI and insert into database
        logging.info("\n--- Step 2: Running AI Processing Service ---")
        run_processor()

    except Exception as e:
        logging.error(f"A critical error occurred in the scrape/process pipeline: {e}", exc_info=True)
    finally:
        logging.info("="*20 + " SCRAPE & PROCESS RUN FINISHED " + "="*20)


if __name__ == "__main__":
    asyncio.run(main())