
import json
import logging
import sys
import os

# Add project root
sys.path.append(os.getcwd())

from src.grading.engine import GraderEngine
from src.grading.parser import PickParser
from src.grading.loader import DataLoader

# Setup logging
logging.basicConfig(level=logging.INFO)

FIXTURE_PATH = "tests/fixtures/goldenset_scores.json"

def debug_failures():
    # Load Fixtures
    with open(FIXTURE_PATH, "r") as f:
        scores = json.load(f)
    engine = GraderEngine(scores)

    # Failed Cases
    debug_cases = [
        {"pick": "Knicks/Nuggets Over 260.5", "league": "nba"},
        {"pick": "Jalen Brunson Over 41.5 Pts", "league": "nba"},
        {"pick": "Boston Bruins ML", "league": "nhl"}, # Debugging the False Win
        {"pick": "Getafe vs Celta Vigo Draw", "league": "laliga"}
    ]

    print(f"--- Debugging {len(debug_cases)} Failures ---")

    for case in debug_cases:
        print(f"\n🔎 Pick: {case['pick']} ({case['league']})")
        
        # 1. Inspect Parse
        try:
            parsed = PickParser.parse(case["pick"], case["league"])
            print(f"   Parsed Type: {parsed.bet_type}")
            print(f"   Selection: '{parsed.selection}'")
            print(f"   Line: {parsed.line}")
            print(f"   Subject: '{parsed.subject}' | Stat: '{parsed.stat}'")
            print(f"   Is Over: {parsed.is_over}") 
        except Exception as e:
            print(f"   ❌ Parse Error: {e}")
            continue

        # 2. Inspect Grade with trace
        graded = engine.grade(parsed)
        print(f"   Grade: {graded.grade.value}")
        print(f"   Summary: {graded.score_summary}")
        print(f"   Details: {graded.details}")
        
        # 3. Deep Dive for Bruins ML
        if "Bruins" in case["pick"]:
            print("   --- Bruins Deep Dive ---")
            # Find game
            from src.grading.matcher import Matcher
            game = Matcher.find_game(parsed.selection, parsed.league, scores)
            if game:
                print(f"   Found Game: {game['team1']} {game['score1']} vs {game['team2']} {game['score2']}")
                picked, opp, is_t1 = Matcher.resolve_picked_team(parsed.selection, game)
                print(f"   Resolved Picked: {picked} (Is Team1? {is_t1})")
                
                # Check winner flags for NHL (some might be implicit)
                print(f"   Winner1: {game.get('winner1')} | Winner2: {game.get('winner2')}")

if __name__ == "__main__":
    debug_failures()
