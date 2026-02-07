
import json
import logging
import sys
import os

# Add project root
sys.path.append(os.getcwd())

FIXTURE_PATH = "tests/fixtures/goldenset_scores.json"

def expand_fixtures():
    if not os.path.exists(FIXTURE_PATH):
        print(f"❌ Fixtures not found at {FIXTURE_PATH}")
        return

    with open(FIXTURE_PATH, "r") as f:
        existing_games = json.load(f)
    
    print(f"Loaded {len(existing_games)} existing games.")
    
    # Synthetic Data for missing sports
    # We use a consistent date 2026-02-05 for these
    
    synthetic_games = [
        # --- TENNIS ---
        {
            "league": "tennis",
            "id": "SYNTH_TENNIS_001",
            "type": "matchup",
            "team1": "Jannik Sinner",
            "score1": "2", # Sets
            "winner1": True,
            "team2": "Carlos Alcaraz",
            "score2": "1", # Sets
            "winner2": False,
            "status": "STATUS_FINAL",
            "team1_data": {"statistics": []},
            "team2_data": {"statistics": []}
            # Note: For tennis totals, we might need more detailed parsing, 
            # but usually regex parser handles "Over 22.5 Games" effectively if grading engine supports it.
            # Grading engine for Tennis usually just checks Match Winner or assumes Sets.
            # If we want Game Totals, we'd need detailed scores. 
            # Let's assume simplest ML for now as that's 90% of tennis bets.
        },
        
        # --- RUGBY ---
        {
            "league": "rugby-union",
            "id": "SYNTH_RUGBY_001",
            "type": "matchup",
            "team1": "South Africa",
            "score1": "32",
            "winner1": True,
            "team2": "New Zealand",
            "score2": "12",
            "winner2": False,
            "status": "STATUS_FINAL",
            "team1_data": {},
            "team2_data": {}
        },
        
        # --- CRICKET ---
        {
            "league": "cricket",
            "id": "SYNTH_CRICKET_001",
            "type": "matchup",
            "team1": "India",
            "score1": "240/3", # Raw score str
            "winner1": True,
            "team2": "Australia",
            "score2": "235/10",
            "winner2": False,
            "status": "STATUS_FINAL",
            "team1_data": {},
            "team2_data": {}
        },
        
        # --- BOXING ---
        {
            "league": "boxing",
            "id": "SYNTH_BOXING_001",
            "type": "matchup",
            "team1": "Tyson Fury",
            "score1": None,
            "winner1": False,
            "team2": "Oleksandr Usyk",
            "score2": None,
            "winner2": True,
            "status": "STATUS_FINAL",
            "team1_data": {},
            "team2_data": {}
        },
        
        # --- NFL (Super Bowl Synthetic) ---
        {
            "league": "nfl",
            "id": "SYNTH_NFL_001",
            "type": "matchup",
            "team1": "Kansas City Chiefs",
            "score1": "31",
            "winner1": True,
            "team2": "San Francisco 49ers",
            "score2": "20",
            "winner2": False,
            "status": "STATUS_FINAL",
            "team1_data": {
                "linescores": [
                    {"period": 1, "value": 7},
                    {"period": 2, "value": 10},
                    {"period": 3, "value": 7},
                    {"period": 4, "value": 7}
                ],
                "statistics": [
                    {"name": "firstDowns", "displayValue": "22"},
                    {"name": "totalYards", "displayValue": "450"}
                ]
            },
            "team2_data": {
                 "linescores": [
                    {"period": 1, "value": 3},
                    {"period": 2, "value": 7},
                    {"period": 3, "value": 3},
                    {"period": 4, "value": 7}
                ],
                "statistics": [
                    {"name": "firstDowns", "displayValue": "18"},
                    {"name": "totalYards", "displayValue": "320"}
                ]
            }
        }
    ]
    
    # Check if already present to avoid duplicates
    existing_ids = {g["id"] for g in existing_games}
    new_games = []
    
    for sg in synthetic_games:
        if sg["id"] not in existing_ids:
            new_games.append(sg)
            
    if not new_games:
        print("No new games to add. Fixtures already contain synthetic data.")
        return

    combined = existing_games + new_games
    
    with open(FIXTURE_PATH, "w") as f:
        json.dump(combined, f, indent=2)
        
    print(f"✅ Added {len(new_games)} synthetic games for missing sports.")
    print(f"Total Fixtures: {len(combined)}")

if __name__ == "__main__":
    expand_fixtures()
