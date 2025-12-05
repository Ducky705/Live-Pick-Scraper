import pytest
from datetime import date
from models import RawPick
from simple_parser import parse_with_regex

# List of (Input Text, Expected Pick Value, Expected Bet Type)
TEST_CASES = [
    ("Lakers -5 -110", "Lakers -5", "Spread"),
    ("Warriors +3.5 -105", "Warriors +3.5", "Spread"),
    ("Lakers ML -150", "Lakers ML", "Moneyline"),
    ("Celtics Moneyline +120", "Celtics ML", "Moneyline"),
    ("o215.5 -110", "Over 215.5", "Total"),
    ("Under 215.5 -110", "Under 215.5", "Total"),
    ("u 210.5", "Under 210.5", "Total"),
    ("Chiefs Pk", "Chiefs -0", "Spread"),
    ("Chiefs Pick'em", "Chiefs -0", "Spread"),
    ("Cowboys -7.5 (2u)", "Cowboys -7.5", "Spread"),
]

@pytest.mark.parametrize("text, expected_val, expected_type", TEST_CASES)
def test_regex_accuracy(text, expected_val, expected_type):
    pick = RawPick(
        id=1, source_unique_id="test", source_url="test", capper_name="test",
        raw_text=text, pick_date=date.today()
    )
    result = parse_with_regex(pick)
    
    assert result is not None, f"Failed to parse: {text}"
    assert result.pick_value == expected_val
    assert result.bet_type == expected_type

def test_unit_extraction():
    cases = [
        ("Lakers -5 2u", 2.0),
        ("Lakers -5 (3units)", 3.0),
        ("Lakers -5 MAX BET", 5.0),
        ("Lakers -5 Whale Play", 5.0),
        ("Lakers -5", 1.0)
    ]
    
    for text, expected_unit in cases:
        pick = RawPick(
            id=1, source_unique_id="test", source_url="test", capper_name="test",
            raw_text=text, pick_date=date.today()
        )
        result = parse_with_regex(pick)
        if result:
            assert result.unit == expected_unit, f"Unit failed for {text}"