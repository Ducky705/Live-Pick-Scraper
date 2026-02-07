
import logging
from unittest.mock import MagicMock, patch
import sys
import os
import types

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock aiohttp logic
mock_aiohttp = MagicMock()
sys.modules["aiohttp"] = mock_aiohttp

from src.game_enricher import enrich_picks

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_odds_enrichment():
    print("Testing Odds Enrichment with Real-Like Data mock...")
    
    # Mock data
    target_date = "2024-01-01"
    
    # Picks representing different bet types
    picks = [
        {"pick": "Lakers ML", "league": "NBA", "odds": None},
        {"pick": "Celtics -5.5", "league": "NBA", "odds": 0},
        {"pick": "Over 220", "league": "NBA", "odds": ""},
        {"pick": "Warriors ML", "league": "NBA", "odds": -150},
    ]
    
    # Mock Response
    mock_odds_data = {
        "nba:1:1": {
            "home_team": "Los Angeles Lakers",
            "away_team": "Golden State Warriors",
            "moneyline_home": -200,
            "moneyline_away": +170,
            "spread_home_odds": -110,
            "spread_away_odds": -110,
            "over_odds": -105,
            "under_odds": -115
        },
        "nba:2:2": {
            "home_team": "Boston Celtics",
            "away_team": "New York Knicks",
            "moneyline_home": -300, 
            "moneyline_away": +250,
            "spread_home_odds": -108, 
            "spread_away_odds": -112,
            "over_odds": -110,
            "under_odds": -110
        }
    }
    
    with patch("src.game_enricher.fetch_scores_for_date") as mock_fetch_scores, \
         patch("src.game_enricher.fetch_odds_for_date") as mock_fetch_odds, \
         patch("src.game_enricher.get_odds_for_pick") as mock_get_odds:
         
        mock_fetch_scores.return_value = [] 
        mock_fetch_odds.return_value = mock_odds_data
        
        # Simple side effect to match picks to odds
        def side_effect(pick_text, league, odds_data):
            pick_lower = pick_text.lower()
            if "lakers" in pick_lower: return mock_odds_data["nba:1:1"]
            if "celtics" in pick_lower: return mock_odds_data["nba:2:2"]
            if "over" in pick_lower: return mock_odds_data["nba:1:1"] 
            return None
            
        mock_get_odds.side_effect = side_effect
        
        enriched = enrich_picks(picks, target_date)
        
        for p in enriched:
            print(f"Pick: {p['pick']:<15} | Odds: {p['odds']}")

if __name__ == "__main__":
    test_odds_enrichment()
