
import sys
import os
import logging
from pprint import pprint

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.score_fetcher import fetch_scores_for_date
from src.score_cache import get_cache

logging.basicConfig(level=logging.INFO)

def main():
    target_date = "2026-02-05"
    print(f"--- Verifying Score Fetcher for {target_date} ---")

    # 1. Check Cache First
    cache = get_cache()
    cached_nba = cache.get_scores("20260205", "nba")
    print(f"Cache state for NBA 20260205: {len(cached_nba) if cached_nba else 'None'}")
    
    # 2. Force Refresh Fetch
    print("Fetching with force_refresh=True...")
    scores = fetch_scores_for_date(target_date, requested_leagues=["nba", "ncaab"], force_refresh=True, final_only=True)
    
    print(f"Fetched {len(scores)} games.")
    
    nba_games = [g for g in scores if g['league'] == 'nba']
    ncaab_games = [g for g in scores if g['league'] == 'ncaab']
    
    print(f"NBA Games: {len(nba_games)}")
    print(f"NCAAB Games: {len(ncaab_games)}")
    
    if nba_games:
        print("\nNBA Matchups:")
        for g in nba_games:
             t1 = g.get('team1', 'Unknown')
             t2 = g.get('team2', 'Unknown')
             print(f"  {t1} vs {t2}")

    if ncaab_games:
        print(f"\nNCAAB Games: {len(ncaab_games)} found.")


if __name__ == "__main__":
    main()
