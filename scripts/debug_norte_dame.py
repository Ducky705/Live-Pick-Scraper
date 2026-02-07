
import sys
import os
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.grading.matcher import Matcher

logging.basicConfig(level=logging.INFO)

def test_norte_dame():
    pick_text = "Norte Dame +18"
    league = "" # Empty league
    
    # Mock game: Notre Dame played who on Feb 5th?
    # I need to know the opponent. Let's assume a generic one or try to fetch from cache.
    # Actually, if I don't know the opponent, I verify if Matcher finds it given a list.
    
    games = [
        {
            "team1": "Notre Dame Fighting Irish",
            "team2": "Syracuse Orange", # Hypothetical opponent
            "league": "NCAAB",
            "date": "2026-02-05"
        }
    ]
    
    print(f"Testing pick: '{pick_text}'")
    
    # 1. Match Game
    print("--- Finding Game ---")
    match = Matcher.find_game(pick_text, league, games)
    if not match:
        print("FAILED: Game not found")
        # Check why
        print("Debugging _find_best_match:")
        Matcher._find_best_match(pick_text, games)
    else:
        print(f"Game Found: {match['team1']} vs {match['team2']}")
        
        # 2. Resolve Team
        print("--- Resolving Team ---")
        picked_team, opponent, success = Matcher.resolve_picked_team(pick_text, match)
        print(f"Result: {picked_team} (Success: {success})")
        
        if not success:
            print("Reason: Resolution failed")
            # Debug _team_in_text
            t1 = match["team1"]
            t2 = match["team2"]
            print(f"  In text '{t1}'? {Matcher._team_in_text(t1, Matcher.normalize(pick_text))}")
            print(f"  In text '{t2}'? {Matcher._team_in_text(t2, Matcher.normalize(pick_text))}")

if __name__ == "__main__":
    test_norte_dame()
