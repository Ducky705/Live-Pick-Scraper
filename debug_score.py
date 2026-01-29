import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.getcwd()))

from src.grading.matcher import Matcher
from src.score_fetcher import fetch_scores_for_date


async def check_score():
    date = "2026-01-24"
    print(f"Fetching scores for {date}...")
    scores = fetch_scores_for_date(date)

    print(f"Found {len(scores)} games.")

    # Search for any Georgia teams
    print("\n--- Searching for 'Georgia' in all games ---")
    for g in scores:
        t1 = g["team1"]
        t2 = g["team2"]
        if "Georgia" in t1 or "Georgia" in t2:
            print(f"  {t1} vs {t2} (League: {g['league']})")

    # Check Georgia Tech
    gt_game = Matcher.find_game("Georgia Tech", "NCAAB", scores)
    if gt_game:
        print("\n--- Georgia Tech Game ---")
        print(f"Match: {gt_game['team1']} vs {gt_game['team2']}")
        print(f"Score: {gt_game['score1']} - {gt_game['score2']}")
        s1 = float(gt_game["score1"] or 0)
        s2 = float(gt_game["score2"] or 0)
        print(f"Total: {s1 + s2}")
    else:
        print("Georgia Tech game not found.")

    # Check Georgia Bulldogs
    ga_game = Matcher.find_game("Georgia", "NCAAB", scores)
    if ga_game:
        print("\n--- Georgia Bulldogs Game ---")
        print(f"Match: {ga_game['team1']} vs {ga_game['team2']}")
        print(f"Score: {ga_game['score1']} - {ga_game['score2']}")
        s1 = float(ga_game["score1"] or 0)
        s2 = float(ga_game["score2"] or 0)
        print(f"Total: {s1 + s2}")


if __name__ == "__main__":
    asyncio.run(check_score())
