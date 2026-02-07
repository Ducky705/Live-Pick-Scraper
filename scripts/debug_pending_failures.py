
import sys
import os
import logging

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from src.grading.parser import PickParser
from src.grading.matcher import Matcher
from src.grading.engine import GraderEngine

# Configure Logging to see Matcher output
logging.basicConfig(level=logging.INFO)

def test_pick(pick_text, game_data):
    print(f"\n--- Testing: '{pick_text}' ---")
    parsed = PickParser.parse(pick_text)
    print(f"Parsed: Type={parsed.bet_type}, Selection='{parsed.selection}', Line={parsed.line}, League={parsed.league}")
    
    # 1. Test Matcher.find_game (should pass if we provide the right game in list)
    found_game = Matcher.find_game(parsed.selection, parsed.league, [game_data])
    if found_game:
        print(f"Game Found: {found_game['team1']} vs {found_game['team2']}")
        
        # 2. Test Resolve Picked Team
        picked, opp, is_t1 = Matcher.resolve_picked_team(parsed.selection, found_game)
        print(f"Resolved Team: '{picked}' (Expected one of {found_game['team1']}, {found_game['team2']})")
        
        # 3. Test Prop resolution (if prop)
        if parsed.bet_type in ["Player Prop", "Team Prop"]:
             # Mock leaders/boxscore
             # Add mock data
             pass
    else:
        print("Game NOT Found via Matcher")

def main():
    # Mock Games
    knicks_game = {
        "id": "1", "league": "NBA",
        "team1": "New York Knicks", "team2": "Miami Heat",
        "team1_display": "Knicks", "team2_display": "Heat",
        "winner1": False, "winner2": True
    }
    
    mavs_game = {
        "id": "2", "league": "NBA",
        "team1": "Dallas Mavericks", "team2": "San Antonio Spurs",
        "winner1": False, "winner2": True
    }
    
    sixers_game = {
        "id": "3", "league": "NBA",
        "team1": "Philadelphia 76ers", "team2": "Boston Celtics",
        "winner1": False, "winner2": True
    }
    
    lakers_game = {
        "id": "4", "league": "NBA",
        "team1": "Los Angeles Lakers", "team2": "Orlando Magic",
        "full_boxscore": [
            {"name": "LeBron James", "team": "Los Angeles Lakers", "points": 28, "rebounds": 8, "assists": 8},
            {"name": "Anthony Davis", "team": "Los Angeles Lakers", "points": 20}
        ]
    }

    # Test Cases
    test_pick("Knicks -4.5 **", knicks_game)
    test_pick("(2u) Mavericks +7 -11", mavs_game)
    test_pick("5u Mavericks +8.5 v. Spurs", mavs_game)
    test_pick("76ers + 4.5", sixers_game)
    test_pick("ers +3.5", sixers_game) # "ers" failure
    
    # Prop Test
    test_pick("LeBron: Pts O 25.5", lakers_game)
    
    # Test Boxscore Flattening
    print("\n--- Testing Boxscore Flattening ---")
    mock_espn_boxscore = {
        "players": [
            {
                "team": {"displayName": "Lakers"},
                "statistics": [
                    {
                        "names": ["MIN", "PTS", "REB"],
                        "keys": ["min", "points", "rebounds"],
                        "athletes": [
                            {
                                "athlete": {"displayName": "LeBron James", "id": "123"},
                                "stats": ["36", "28", "8"]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    engine = GraderEngine([])
    flat = engine._flatten_boxscore(mock_espn_boxscore)
    print(f"Flattened Boxscore (First Player): {flat[0] if flat else 'Empty'}")
    
    # Verify values
    if flat and flat[0].get("points") == "28":
        print("SUCCESS: Points extracted correctly.")
    else:
        print("FAILURE: Points extraction failed.")

    # Test "Mavs" alias explicitly
    print(f"\nChecking 'Mavs' vs 'Dallas Mavericks': {Matcher._team_in_text('Dallas Mavericks', 'mavs')}")
    print(f"Checking 'Knicks' vs 'New York Knicks': {Matcher._team_in_text('New York Knicks', 'knicks')}")
    print(f"Checking '76ers' vs 'Philadelphia 76ers': {Matcher._team_in_text('Philadelphia 76ers', '76ers')}")

if __name__ == "__main__":
    main()
