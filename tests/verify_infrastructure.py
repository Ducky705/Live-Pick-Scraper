import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.score_fetcher import fetch_scores_for_date

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InfraCheck")


async def check_scores():
    date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    logger.info(f"Fetching scores for {date_str}...")

    try:
        scores = fetch_scores_for_date(date_str)
        logger.info(f"Fetched {len(scores)} games.")

        if not scores:
            logger.warning("No scores returned!")
            return

        # Check structure of first few games of different leagues
        leagues_seen = set()
        for game in scores:
            lg = game.get("league")
            if lg not in leagues_seen:
                leagues_seen.add(lg)
                logger.info(f"\n--- Structure for {lg} ---")
                logger.info(json.dumps(game, indent=2, default=str)[:500] + "...")

                # Check critical keys
                required = ["team1", "score1", "winner1"]
                missing = [k for k in required if k not in game]
                if missing:
                    logger.error(f"  MISSING KEYS in {lg}: {missing}")
                else:
                    logger.info(f"  Keys valid for {lg}")

    except Exception as e:
        logger.error(f"Error fetching scores: {e}")


if __name__ == "__main__":
    asyncio.run(check_scores())
