import asyncio
import logging
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.score_fetcher import fetch_scores_for_date

logging.basicConfig(level=logging.INFO)


async def dump_scores():
    date_str = "2026-01-24"
    print(f"Fetching scores for {date_str}...")
    scores = fetch_scores_for_date(date_str)

    print(f"Fetched {len(scores)} games.")
    for g in scores:
        t1 = g.get("team1")
        t2 = g.get("team2")
        lg = g.get("league")
        if t1 and t2:
            print(f"[{lg}] {t1} vs {t2}")


if __name__ == "__main__":
    asyncio.run(dump_scores())
