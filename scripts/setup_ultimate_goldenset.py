
import sys
import os
import re
import json
import logging
from typing import Any

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.score_cache import get_cache
# from src.grading.schema import Grade

# Paths
REPORT_PATH = "src/data/output/dry_run_analysis_2026-02-05.md"
GOLDENSET_PATH = "tests/goldenset.json"
FIXTURES_PATH = "tests/fixtures/goldenset_scores.json"

def clean_pick_text(text: str) -> str:
    """Clean markdown table artifacts from pick text."""
    # Remove leading/trailing pipes and whitespace
    text = text.strip().strip('|').strip()
    return text

def extract_failures():
    print(f"Reading report from {REPORT_PATH}...")
    with open(REPORT_PATH, "r") as f:
        content = f.read()

    # Find the Detailed Pick List table
    # Look for header, then capture everything until a new header (##) or EOF
    match = re.search(r"## 5\. Detailed Pick List\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    if not match:
        print("Could not find Detailed Pick List table.")

        return []

    table_text = match.group(1)
    lines = table_text.strip().split('\n')
    
    # Skip header lines (first 2)
    rows = lines[2:]
    
    failures = []
    
    for row in rows:
        parts = [p.strip() for p in row.split('|')]
        # | Capper | League | Pick | Odds | Grade | Summary |
        # parts[0] is empty (leading pipe), parts[1] is Capper, parts[2] is League, etc.
        if len(parts) < 7:
            continue
            
        league = parts[2]
        pick_text = parts[3]
        grade = parts[5]
        
        # Criteria for inclusion: UNKNOWN league or PENDING grade
        if league == "UNKNOWN" or "PENDING" in grade or "Game not found" in parts[6]:
            test_case = {
                "desc": f"Fix: {pick_text[:30]}...",
                "pick": pick_text,
                "league": league if league != "UNKNOWN" else "", # Empty league implies auto-detect needed
                "expected": "RESOLVED", # Special tag for 'Any definitive grade'
                "game_id": "ANY" 
            }
            failures.append(test_case)
            
    print(f"Extracted {len(failures)} failures.")
    return failures

def dump_scores():
    print("Dumping scores for 2026-02-05...")
    cache = get_cache()
    
    all_games = []
    leagues = ["nba", "ncaab", "nhl", "tennis", "nfl", "mlb", "ufc", "boxing", "cricket", "rugby-union", "esports"] # Add others as needed
    
    for league in leagues:
        games = cache.get_scores("20260205", league)
        if games:
            print(f"  {league}: {len(games)} games")
            all_games.extend(games)
            
    print(f"Total games dumped: {len(all_games)}")
    return all_games

def main():
    # 1. Extract Failures
    failures = extract_failures()
    
    # 2. Dump Scores
    scores = dump_scores()
    
    # 3. Write Goldenset
    with open(GOLDENSET_PATH, "w") as f:
        json.dump(failures, f, indent=4)
    print(f"Wrote {GOLDENSET_PATH}")
    
    # 4. Write Scores
    with open(FIXTURES_PATH, "w") as f:
        json.dump(scores, f, indent=4)
    print(f"Wrote {FIXTURES_PATH}")

if __name__ == "__main__":
    main()
