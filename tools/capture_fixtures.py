
import json
import logging
import sys
import os
from datetime import datetime

# Add project root
sys.path.append(os.getcwd())

from src.grading.loader import DataLoader

# Setup logging
logging.basicConfig(level=logging.INFO)

FIXTURE_PATH = "tests/fixtures/goldenset_scores.json"

def capture_fixtures():
    # Define our "Goldenset" dates
    # We mix dates to get variety of sports
    requests = [
        {"date": "2026-02-04", "leagues": ["nba", "nhl"]},  # Core US Sports
        {"date": "2026-02-01", "leagues": ["epl", "laliga"]}, # Soccer Sunday
        {"date": "2026-01-24", "leagues": ["ufc"]},         # Fight Night
    ]
    
    all_games = []
    
    print(f"Capturing fixtures to {FIXTURE_PATH}...")
    
    for req in requests:
        date = req["date"]
        leagues = req["leagues"]
        print(f"Fetching {date} for {leagues}...")
        
        scores = DataLoader.fetch_scores([date], leagues)
        print(f"  Got {len(scores)} games.")
        
        # Add to collection
        all_games.extend(scores)

    # Dedup just in case
    unique_games = {g["id"]: g for g in all_games}.values()
    final_list = list(unique_games)
    
    # Save
    os.makedirs(os.path.dirname(FIXTURE_PATH), exist_ok=True)
    with open(FIXTURE_PATH, "w") as f:
        json.dump(final_list, f, indent=2)
        
    print(f"\n✅ Saved {len(final_list)} games to {FIXTURE_PATH}")
    
    # Print summary for test case creation
    summary = {}
    for g in final_list:
        lg = g.get("league")
        summary.setdefault(lg, []).append(f"{g['team1']} vs {g['team2']} ({g['score1']}-{g['score2']}) ID:{g['id']}")
        
    for lg, games in summary.items():
        print(f"\n{lg.upper()}:")
        for line in games[:5]: # Show first 5
            print(f"  {line}")

if __name__ == "__main__":
    capture_fixtures()
