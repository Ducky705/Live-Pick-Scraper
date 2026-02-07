
import json
import logging
import sys
import os
from datetime import datetime, timedelta

# Add project root
sys.path.append(os.getcwd())

from src.grading.loader import DataLoader
from src.grading.engine import GraderEngine
from src.grading.schema import GradeResult

# Setup logging
logging.basicConfig(level=logging.INFO)

def run_tests():
    # TEST DATE: Check both Feb 4 and Feb 5
    TEST_DATES = ["2026-02-04", "2026-02-05"]
    print(f"--- Grading Specific Pick for {TEST_DATES} ---")

    # 1. Fetch Scores
    leagues = ["nba"] 
    print(f"Fetching scores for: {leagues}...")
    scores = DataLoader.fetch_scores(TEST_DATES, leagues)
    print(f"Fetched {len(scores)} games.")
    
    # Print available games
    print("\n--- Available Games ---")
    for g in scores:
        print(f"[{g.get('league').upper()}] {g.get('team1')} vs {g.get('team2')} ({g.get('score1')}-{g.get('score2')}) Status: {g.get('status')}")

    # 2. Find Clippers Game manually
    clippers_game = None
    for g in scores:
        if "Clippers" in g.get("team1") or "Clippers" in g.get("team2"):
            clippers_game = g
            break
            
    if not clippers_game:
        print("❌ Clippers game not found!")
        return

    print(f"Found Clippers game: {clippers_game['team1']} vs {clippers_game['team2']}")
    
    # 3. Fetch Boxscore
    print("Fetching boxscore...")
    boxscore = DataLoader.fetch_boxscore(clippers_game)
    
    # 4. Find Kawhi
    kawhi_stats = None
    for p in boxscore:
        if "Kawhi" in p.get("name", ""):
            kawhi_stats = p
            break
            
    if kawhi_stats:
        print(f"Kawhi Leonard Stats: {kawhi_stats}")
        pts = kawhi_stats.get("points") or kawhi_stats.get("pts")
        print(f"Points: {pts}")
        
        # Grade it manually
        line = 24.5
        if float(pts) < line:
            print("Picked Under 24.5 -> WIN")
        else:
            print("Picked Under 24.5 -> LOSS")
    else:
        print("❌ Kawhi Leonard not found in boxscore (Did he play?)")


if __name__ == "__main__":
    run_tests()
