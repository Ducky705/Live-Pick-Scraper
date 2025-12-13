import pytest
from standardizer import standardize_league, standardize_bet_type, format_pick_value

def test_standardize_league():
    assert standardize_league("NCAA Football") == "NCAAF"
    assert standardize_league("College Basketball") == "NCAAB"

def test_standardize_bet_type():
    assert standardize_bet_type("ML") == "Moneyline"
    assert standardize_bet_type("ATS") == "Spread"

def test_format_pick_value():
    assert format_pick_value("o 210", "Total", "NBA") == "Over 210"
    assert format_pick_value("lakers ml", "Moneyline", "NBA") == "Lakers ML"
