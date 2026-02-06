import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.grading.matcher import Matcher
from src.grading.vector_index import VectorIndex

def test_ambiguity():
    print("Testing VectorIndex Ambiguity...")
    
    # Scenario: User says "Kings", but both SAC (NBA) and LA (NHL) are playing
    games = [
        {"id": "g1", "team1": "Sacramento Kings", "team2": "Lakers", "league": "NBA"},
        {"id": "g2", "team1": "Los Angeles Kings", "team2": "Oilers", "league": "NHL"},
        # Padding to trigger vector logic (>50 games)
    ] + [{"id": f"dummy_{i}", "team1": f"Team {i}", "team2": f"Opp {i}", "league": "Other"} for i in range(60)]
    
    # 1. Test Matcher behavior
    print("\n--- Matcher.find_game('Kings', 'Other') ---")
    match = Matcher.find_game("Kings", "Other", games)
    if match:
        print(f"Result: Found {match.get('team1')} ({match.get('league')})")
    else:
        print("Result: None (Ambiguous or Not Found)")

    # 2. Inspect VectorIndex scores directly
    print("\n--- Direct VectorIndex Query ---")
    index = VectorIndex()
    for g in games:
        index.add(Matcher.normalize(g["team1"]), g)
        index.add(Matcher.normalize(g["team2"]), g)
    index.build()
    
    results = index.query("kings", top_k=3)
    for meta, score in results:
        print(f"  {meta.get('team1')}: {score:.4f}")

if __name__ == "__main__":
    test_ambiguity()
