
import sys
import os
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.grading.matcher import Matcher

logging.basicConfig(level=logging.INFO)

def test_ers():
    pick_text = "5u ers +3.5 v. Lakers"
    league = "NBA"
    
    # Mock game
    games = [
        {
            "team1": "Philadelphia 76ers",
            "team2": "Los Angeles Lakers",
            "league": "NBA",
            "date": "2026-02-05"
        }
    ]
    
    print(f"Testing pick: '{pick_text}'")
    
    # 1. Match Game
    match = Matcher.find_game(pick_text, league, games)
    if not match:
        print("FAILED: Game not found")
        return

    print(f"Game Found: {match['team1']} vs {match['team2']}")
    
    # 2. Resolve Team
    picked_team, opponent, success = Matcher.resolve_picked_team(pick_text, match)
    
    print(f"Result: {picked_team} (Success: {success})")
    if not success:
        print("Reason: Resolution failed")

if __name__ == "__main__":
    test_ers()
