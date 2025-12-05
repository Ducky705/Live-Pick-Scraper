import pytest
from models import ParsedPick

def test_odds_sanity_check():
    # Valid Odds
    p = ParsedPick(raw_pick_id=1, league="NBA", bet_type="ML", pick_value="X", odds_american=-110)
    assert p.odds_american == -110

    # Impossible Odds (OCR Error: -11000)
    p = ParsedPick(raw_pick_id=1, league="NBA", bet_type="ML", pick_value="X", odds_american=-110000)
    assert p.odds_american is None # Should validate to None

def test_spread_warning_heuristic():
    # Normal Spread
    p = ParsedPick(raw_pick_id=1, league="NBA", bet_type="Spread", pick_value="Lakers -5")
    # No error expected
    
    # Suspicious Spread (Likely Total)
    p = ParsedPick(raw_pick_id=1, league="NBA", bet_type="Spread", pick_value="Lakers -210.5")
    assert p.pick_value == "Lakers -210.5"