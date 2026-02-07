import json
import time
import sys
import os
import logging
from dataclasses import asdict

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.grading.parser import PickParser
from src.grading.matcher import Matcher

# Suppress logs for speed
logging.getLogger("src.grading.vector_index").setLevel(logging.ERROR)

V4_PATH = "benchmark/dataset/golden_set_v4.json"

def synthesize_game(pick_data):
    """Create a dummy game that SHOULD match the expected pick."""
    # This is a heuristic. If pick is "Georgia -6", we need a game with "Georgia".
    # We'll use the 'pick' text or 'capper_name' if available, but expected_picks usually has the normalized pick.
    
    # We parse the Expected Pick string to guess the team? 
    # Or we just assume the parser output is the truth for matching?
    # Actually, to test MATCHING, we need a game that represents the correct answer.
    # We can try to extract the team from the expected 'pick' string.
    
    pick_str = pick_data.get("pick", "")
    league = pick_data.get("league", "UNKNOWN")
    
    # Heuristic: just use the whole pick string as the team name for the synthetic game?
    # No, that's cheating. "Georgia -6" isn't a team name.
    # But for now, let's skip synthesization for the FIRST pass and just test PARSING accuracy.
    # Matching accuracy requires a ground truth "Game ID" which V4 doesn't seem to have?
    return None

def run_v4_benchmark():
    print(f"--- Running Golden Set V4 Accuracy Benchmark ---")
    
    if not os.path.exists(V4_PATH):
        print(f"File not found: {V4_PATH}")
        return

    with open(V4_PATH, "r") as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} samples.")
    
    parser = PickParser()
    
    total_samples = 0
    parsed_count = 0
    correct_league_count = 0
    
    start_time = time.time()
    
    # Speed metrics
    parse_times = []
    
    for i, item in enumerate(data):
        raw_text = item.get("text", "")
        expected_list = item.get("expected_picks", [])
        
        if not expected_list:
            continue
            
        total_samples += 1
        print(f"[{i}] Parsing: {raw_text[:50]}...") # Debug
        
        t0 = time.time()
        picks = parser.parse(raw_text)
        dt = time.time() - t0
        parse_times.append(dt)
        
        # Check if we got *any* picks
        if picks:
            parsed_count += 1
            
            # Rough accuracy check: Did we find the right number of picks?
            # And represents the league correctly?
            
            # Compare first pick logic
            p = picks
            exp = expected_list[0] # Assume primary pick
            
            # Check League Match
            if p.league and exp.get("league") and p.league.upper() == exp.get("league").upper():
                correct_league_count += 1
                
    total_time = time.time() - start_time
    avg_parse_time = sum(parse_times) / len(parse_times) if parse_times else 0
    
    print("\n--- Results ---")
    print(f"Total Samples: {total_samples}")
    print(f"Parsed Successfully (Non-Empty): {parsed_count} ({parsed_count/total_samples:.1%})")
    print(f"League Accuracy: {correct_league_count} ({correct_league_count/total_samples:.1%})")
    print(f"\n--- Speed (Parsing Only) ---")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Avg Time per Pick: {avg_parse_time*1000:.2f}ms")
    
    # Validate Matching Speed (Synthetic)
    # print(f"\n--- Benchmarking Matcher Speed (Synthetic) ---")
    # visual/stress test: Create 5000 dummy games
    # games = [{"id": f"g_{i}", "team1": f"Team_{i}", "team2": f"Opp_{i}", "league": "NBA"} for i in range(5000)]
    
    # Query with a subset of V4 texts
    # match_times = []
    # for i in range(min(100, len(data))):
    #     text = data[i].get("text", "Unknown")
    #     t0 = time.time()
    #     Matcher.find_game(text, "NBA", games)
    #     match_times.append(time.time() - t0)
        
    # avg_match = sum(match_times) / len(match_times)
    # print(f"Avg Match Time (vs 5000 games): {avg_match*1000:.2f}ms")
    # print(f"Projected Throughput: {1/avg_match:.0f} picks/sec")


if __name__ == "__main__":
    run_v4_benchmark()
