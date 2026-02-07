from src.grading.matcher import Matcher
from src.grading.parser import PickParser

def test_matcher():
    games = [
        {"team1": "Florida Atlantic", "team2": "UAB", "league": "ncaab", "id": "1"},
        {"team1": "Navy", "team2": "Army", "league": "ncaab", "id": "2"},
        {"team1": "Boston Celtics", "team2": "Knicks", "league": "nba", "id": "3"}
    ]
    
    cases = [
        ("Fau +2.5 **", "ncaab"),
        ("5U Navy ML", "ncaab"),
        ("Celtics -5", "nba")
    ]
    
    print("--- Matcher Debug ---")
    for text, league in cases:
        print(f"Original: '{text}'")
        parsed = PickParser.parse(text, league)
        print(f"Parsed Selection: '{parsed.selection}'")
        
        match = Matcher.find_game(parsed.selection, league, games)
        if match:
            print(f"MATCH FOUND: {match['team1']} vs {match['team2']}")
        else:
            print("MATCH FAILED")
        print("-" * 20)

if __name__ == "__main__":
    test_matcher()
