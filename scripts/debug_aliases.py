import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.grading.matcher import Matcher
import src.team_aliases
from src.team_aliases import TEAM_ALIASES

print(f"DEBUG: Loaded TEAM_ALIASES from: {src.team_aliases.__file__}")

def test_alias(text, league):
    print(f"Testing text: '{text}' (League: {league})")
    
    # Mock games list for testing
    games = [
        {"team1": "Philadelphia 76ers", "team2": "Boston Celtics", "league": "NBA"},
        {"team1": "San Antonio Spurs", "team2": "Dallas Mavericks", "league": "NBA"},
    ]
    
    # 1. Normalize
    norm = Matcher.normalize(text)
    print(f"Normalized: '{norm}'")
    
    # 2. Check Matcher logic
    match = Matcher.find_game(text, league, games)
    if match:
        print(f"Match FOUND: {match['team1']} vs {match['team2']}")
    else:
        print("Match FAILED")
        
    # Deep dive into _team_in_text for specific teams
    print("\nDeep Dive:")
    teams_to_check = ["Philadelphia 76ers", "Dallas Mavericks"]
    for t in teams_to_check:
        is_in = Matcher._team_in_text(t, norm)
        print(f"  Is '{t}' in text? -> {is_in}")
        if not is_in:
             # Check aliases manually to see why
             aliases = TEAM_ALIASES.get(t.lower(), [])
             print(f"  Aliases for {t}: {aliases}")

print("--- Test 1: 'ers' ---")
test_alias("(6u) ers +4.5", "UNKNOWN")

print("\n--- Test 2: 'Mavericks' ---")
test_alias("5u Mavericks +8.5 v. Spurs", "UNKNOWN")
