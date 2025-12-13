import pytest
from models import ParsedPick

def test_parsed_pick_validation():
    # Valid
    p = ParsedPick(
        raw_pick_id=1, league="NBA", bet_type="Spread", 
        pick_value="Lakers -5", odds_american=-110, unit=1.0
    )
    assert p.odds_american == -110

    # Invalid Odds (Too high, likely OCR error)
    p = ParsedPick(
        raw_pick_id=1, league="NBA", bet_type="Spread", 
        pick_value="Lakers -5", odds_american=-150000
    )
    assert p.odds_american is None

    # Invalid Unit parsing
    p = ParsedPick(
        raw_pick_id=1, league="NBA", bet_type="Spread", 
        pick_value="Lakers -5", unit="NotANumber"
    )
    assert p.unit is None
    
    # Unit String Parsing
    p = ParsedPick(
        raw_pick_id=1, league="NBA", bet_type="Spread", 
        pick_value="Lakers -5", unit="5u"
    )
    assert p.unit == 5.0
