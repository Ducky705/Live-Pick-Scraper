import time
import sys
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.grading.matcher import Matcher
from src.grading.vector_index import VectorIndex

def test_vector_match():
    print("Testing VectorIndex directly...")
    
    # Create Dummy Index
    index = VectorIndex()
    teams = ["Los Angeles Lakers", "Golden State Warriors", "Chicago Bulls"]
    for t in teams:
        index.add(t, {"name": t})
        
    start_build = time.time()
    index.build()
    print(f"Build time: {(time.time() - start_build)*1000:.2f}ms")
    
    # Query
    start_query = time.time()
    res = index.query("Lakers", top_k=1)
    print(f"Query result: {res}")
    print(f"Query time: {(time.time() - start_query)*1000:.2f}ms")
    
    # Test through Matcher
    print("\nTesting Matcher.find_game logic...")
    games = [{"id": "1", "team1": "Los Angeles Lakers", "team2": "Boston Celtics", "league": "NBA"}]
    # We need > 50 games to trigger vector logic
    games_padding = [{"id": f"dummy_{i}", "team1": "A", "team2": "B", "league": "NBA"} for i in range(60)]
    all_games = games + games_padding
    
    start_match = time.time()
    match = Matcher.find_game("Lakers", "NBA", all_games)
    print(f"Match found: {match.get('team1') if match else 'None'}")
    print(f"Matcher time: {(time.time() - start_match)*1000:.2f}ms")

if __name__ == "__main__":
    test_vector_match()
