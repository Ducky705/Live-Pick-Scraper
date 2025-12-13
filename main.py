import asyncio
import logging
import argparse
import sys
from datetime import datetime

import config
from scrapers import run_scrapers
from processing_service import process_picks
from database import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_pipeline(force=False):
    logger.info("🚀 STARTING SNIPER PIPELINE")
    
    # --- PHASE 1: SCRAPE TODAY'S PICKS ---
    # We purposefully catch errors here so Processing (Phase 3) still runs
    try:
        logger.info(f"📡 Checking Telegram (Force Full Day: {force})...")
        await run_scrapers(force=force)
    except Exception as e:
        logger.error(f"❌ Scraper Crashed: {e}")

    # --- PHASE 2: EFFICIENCY CHECK ---
    try:
        pending_picks = db.get_pending_raw_picks(limit=1)
        if not pending_picks:
            logger.info("🛑 No new picks & no pending retries. SHUTTING DOWN.")
            sys.exit(0)
    except Exception as e:
        logger.error(f"Error checking DB status: {e}")

    # --- PHASE 3: PROCESS BATCHES ---
    logger.info("🧠 Work detected! Running AI Processor...")
    try:
        # Run 2 batches max to respect GitHub Action limits
        for i in range(2): 
            if not db.get_pending_raw_picks(limit=1):
                break
            process_picks()
            await asyncio.sleep(1) 
    except Exception as e:
        logger.error(f"❌ Processor Crashed: {e}")

    # --- PHASE 4: CLEANUP ---
    try:
        db.archive_old_picks(config.ARCHIVE_AFTER_HOURS)
    except: pass

    logger.info("🏁 Pipeline Finished")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Force re-scrape of the entire day (00:00 ET)")
    args = parser.parse_args()
    asyncio.run(run_pipeline(force=args.force))
