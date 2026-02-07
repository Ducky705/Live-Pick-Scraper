
import sys
import os
import logging
from pprint import pprint

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from src.grader import grade_picks
from src.score_fetcher import fetch_scores_for_date

# Configure logging
logging.basicConfig(level=logging.INFO)

def verify_tennis_grading():
    print("Verifying Tennis Grading Logic...")
    
    # Date with known tennis matches (from previous fetch verification)
    target_date = "2026-02-05"
    
    print(f"Fetching scores for {target_date}...")
    scores = fetch_scores_for_date(target_date, requested_leagues=["atp", "wta"])
    print(f"Fetched {len(scores)} scores.")
    
    # Inspect a few to confirm leagues
    leagues_found = set(g.get("league") for g in scores)
    print(f"Leagues found: {leagues_found}")
    
    if "wta" not in leagues_found:
        print("WARNING: No WTA games found. Check date or fetcher.")
    
    # Define Test Picks
    # We need to find a real match to test against.
    # From previous output: "Naoko Eto" vs "Anastasia Kulikova" (WTA)
    # Winner: Kulikova (Team 2)
    
    test_picks = [
        # Case 1: Explicit WTA pick
        {
            "pick": "Anastasia Kulikova ML",
            "league": "WTA", # Should map to 'wta' and find game
            "date": target_date
        },
        # Case 2: General "Tennis" pick (The problem case)
        {
            "pick": "Anastasia Kulikova ML",
            "league": "Tennis", # Maps to 'atp', might miss WTA game if strict
            "date": target_date
        },
        # Case 3: ATP Pick (if any ATP games exist)
        # We need to find an ATP game name dynamically or guess
    ]
    
    print("\nGrading Picks...")
    graded = grade_picks(test_picks, scores)
    
    for p in graded:
        print(f"Pick: {p.get('pick')} | League: {p.get('league')} | Result: {p.get('result')} | Summary: {p.get('score_summary')}")

if __name__ == "__main__":
    verify_tennis_grading()
