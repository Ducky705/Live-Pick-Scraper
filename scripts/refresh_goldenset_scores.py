
import sys
import os
import json
import logging
from datetime import datetime

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.score_fetcher import fetch_scores_for_date

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TARGET_DATE = "2026-02-05"
OUTPUT_FILE = "tests/fixtures/goldenset_scores.json"

def main():
    logger.info(f"Refresing goldenset scores for {TARGET_DATE}...")
    
    # 1. Fetch ALL scores (force refresh to bypass cache and get live API data)
    # We want final_only=False locally just in case, or True? 
    # Usually goldenset is post-game, so final_only=True is safer to avoid live noise.
    # But if games are missing because they were "in progress" at dry run time, we might miss them.
    # Let's trust final_only=True implies the day is done.
    
    scores = fetch_scores_for_date(TARGET_DATE, force_refresh=True, final_only=False)
    
    if not scores:
        logger.error("No scores found! Aborting update.")
        return
        
    logger.info(f"Fetched {len(scores)} games.")
    
    # 2. Filter validation
    # Check if Celtics are there
    celtics = [g for g in scores if "celtics" in g.get("team1", "").lower() or "celtics" in g.get("team2", "").lower()]
    if celtics:
        logger.info(f"Found Celtics game: {celtics[0]['team1']} vs {celtics[0]['team2']} (Date: {celtics[0].get('date', 'Unknown')})")
    else:
        logger.warning(f"Still no Celtics game found for {TARGET_DATE}!")

    # 3. Save to fixture
    try:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(scores, f, indent=2)
        logger.info(f"Successfully updated {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Failed to write output: {e}")

if __name__ == "__main__":
    main()
