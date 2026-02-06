import time
import sys
import os
import random

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.grading.matcher import Matcher

def generate_dummy_games(n=1000):
    teams = [
        "Lakers", "Warriors", "Bulls", "Celtics", "Heat", "Knicks", "Nets", "76ers",
        "Bucks", "Hawks", "Hornets", "Wizards", "Magic", "Pacers", "Pistons", "Cavaliers",
        "Raptors", "Suns", "Clippers", "Kings", "Mavericks", "Rockets", "Spurs", "Grizzlies",
        "Thunder", "Pelicans", "Trail Blazers", "Nuggets", "Timberwolves", "Jazz"
    ]
    games = []
    for i in range(n):
        t1 = random.choice(teams)
        t2 = random.choice(teams)
        while t1 == t2:
            t2 = random.choice(teams)
        
        games.append({
            "id": f"game_{i}",
            "team1": t1,
            "team2": t2,
            "league": "NBA",
            "team1_data": {"leaders": []},
            "team2_data": {"leaders": []}
        })
    return games

def benchmark_matching():
    # Setup
    print("Generating 5000 dummy games...")
    games = generate_dummy_games(5000)
    
    # Test cases
    picks = [
        "Lakers ML", "Golden State Warriors -5.5", "Chicago Bulls over 220", 
        "NYK Knicks", "Brooklyn Nets", "Sixers", "Giannis Antetokounmpo", # Player mapping
        "LeBron James", "Steph Curry over 30.5", "Tatum under 25"
    ]
    
    # Repeat picks to get significant volume
    test_picks = picks * 200 # 2000 picks
    
    print(f"Benchmarking matching for {len(test_picks)} picks against {len(games)} games...")
    
    start_time = time.time()
    
    matches_found = 0
    for p in test_picks:
        match = Matcher.find_game(p, "NBA", games)
        if match:
            matches_found += 1
            
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Time: {duration:.4f} seconds")
    print(f"Speed: {len(test_picks) / duration:.2f} picks/sec")
    print(f"Matches found: {matches_found}/{len(test_picks)}")

if __name__ == "__main__":
    benchmark_matching()
