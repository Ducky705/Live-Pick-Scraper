
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

def verify_player_props():
    print("Verifying Player Prop Matching...")
    
    # Date: 2026-02-05 (Assuming NBA games happened)
    target_date = "2026-02-05"
    
    print(f"Fetching scores for {target_date}...")
    scores = fetch_scores_for_date(target_date, requested_leagues=["nba"])
    print(f"Fetched {len(scores)} NBA games.")
    
    # We need a player who played but likely WASN'T a leader to test the "Roster Search" necessity.
    # Or just someone whose team isn't mentioned.
    # Let's try 3 known players from real games on this date (if any).
    # If no real games, we might need to mock.
    # Assuming NBA is active.
    
    if not scores:
        print("No NBA scores found. Cannot run live verification.")
        return

    # Let's verify what data we have
    # Pick the first game
    game = scores[0]
    t1 = game['team1']
    t2 = game['team2']
    print(f"Game: {t1} vs {t2}")
    
    # Try to find a player in this game who is NOT in leaders
    # We need to fetch boxscore manually here to find a bench player
    from src.grading.engine import GraderEngine
    engine = GraderEngine(scores)
    boxscore = engine._get_boxscore(game)
    
    test_player = "Unknown"
    bench_player_stat = "0"
    
    if boxscore:
        # Sort by points, pick someone in middle
        # boxscore is list of dicts: {name, points, ...}
        # Find someone with > 0 points but not a star?
        for p in boxscore:
             try:
                 pts = float(p.get("points", 0))
                 if 5 < pts < 15: # Role player
                     test_player = p["name"]
                     bench_player_stat = str(pts)
                     break
             except:
                 continue
                 
    print(f"Test Player (Bench/Role): {test_player} (Pts: {bench_player_stat})")
    
    if test_player == "Unknown":
        print("No leaders found in game data. Hard to verify.")
        return

    test_picks = [
        # Case 1: Team mentioned (Control)
        {
            "pick": f"{t1}: {test_player} Over 0.5 Pts",
            "league": "NBA",
            "date": target_date
        },
        # Case 2: Team NOT mentioned (The Issue)
        {
            "pick": f"{test_player} Over 0.5 Pts",
            "league": "NBA",
            "date": target_date
        },
        # Case 3: Partial Name / Fuzzy (e.g. "Davis" for "Anthony Davis")
        # We need to manually split the name
        {
            "pick": f"{test_player.split()[-1]} Over 0.5 Pts",
            "league": "NBA",
            "date": target_date
        },
        # Case 4: Typo (Fuzzy Match)
        {
            "pick": f"{test_player[:-2]}xx Over 0.5 Pts", # e.g. "Justin Champagnxx"
            "league": "NBA",
            "date": target_date
        }
    ]
    
    print("\nGrading Picks...")
    # Debug Parser first
    from src.grading.parser import PickParser
    for i, p in enumerate(test_picks):
        parsed = PickParser.parse(p["pick"], p["league"], p["date"])
        print(f"Debug Parse [{i}]: Text='{parsed.raw_text}' | Subject='{parsed.subject}' | Stat='{parsed.stat}' | Type='{parsed.bet_type}'")

    graded = grade_picks(test_picks, scores)
    
    for p in graded:
        status = "✅ PASS" if p.get("result") != "Pending" else "❌ FAIL"
        print(f"Pick: {p.get('pick'):<40} | Result: {p.get('result'):<10} | {status} | {p.get('score_summary')}")

if __name__ == "__main__":
    verify_player_props()
