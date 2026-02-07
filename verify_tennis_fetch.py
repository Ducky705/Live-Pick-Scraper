
import sys
import os
import logging
import json

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from score_fetcher import fetch_scores_for_date

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)

def test_tennis_fetch():
    print("Testing Tennis Score Fetching...")
    
    # Pick a recent date where tennis matches likely occurred
    # e.g., Yesterday? Or today?
    # Let's try 2025-02-05 (User's yesterday, roughly)
    # Or 2024-05-26 (French Open)?
    # Since we are fetching from ESPN API, we need a real date with matches.
    # User's current time is 2026-02-06.
    # Let's try 2026-02-05 (Yesterday) or today.
    target_date = "2026-02-05"
    
    scores = fetch_scores_for_date(
        target_date, 
        requested_leagues=["atp", "wta"], 
        force_refresh=True,
        final_only=False # Fetch all to see if we get anything
    )
    
    print(f"Fetched {len(scores)} tennis matches for {target_date}.")
    
    if scores:
        print("\nSample Match:")
        print(json.dumps(scores[0], indent=2))
        
        # Check integrity
        valid = 0
        for s in scores:
            if "winner1" in s and "winner2" in s:
                valid += 1
        print(f"\nMatches with winner status: {valid}/{len(scores)}")
    else:
        print("No matches found. This might mean:")
        print("1. No matches on this date.")
        print("2. Endpoints are wrong.")
        print("3. Parser logic is skipping them.")

if __name__ == "__main__":
    test_tennis_fetch()
