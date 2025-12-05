import pytest
from simple_parser import parse_with_regex, _stitch_lines
from models import RawPick
from datetime import date

@pytest.fixture
def sample_raw_pick():
    return RawPick(
        id=1, source_unique_id="1", source_url="", capper_name="Test", 
        raw_text="", pick_date=date.today()
    )

def test_line_stitching():
    lines = ["Los Angeles Lakers", "-5 -110"]
    stitched = _stitch_lines(lines)
    assert len(stitched) == 1
    assert stitched[0] == "Los Angeles Lakers -5 -110"

def test_implicit_spread(sample_raw_pick):
    sample_raw_pick.raw_text = "Lakers -5"
    res = parse_with_regex(sample_raw_pick)
    assert res is not None
    assert res.bet_type == "Spread"
    assert res.pick_value == "Lakers -5"

def test_short_total(sample_raw_pick):
    sample_raw_pick.raw_text = "o215.5"
    res = parse_with_regex(sample_raw_pick)
    assert res is not None
    assert res.bet_type == "Total"
    assert res.pick_value == "Over 215.5"

def test_stitched_parsing(sample_raw_pick):
    # This simulates a screenshot where OCR split the lines
    sample_raw_pick.raw_text = "Chiefs\n-3 -115"
    res = parse_with_regex(sample_raw_pick)
    assert res is not None
    assert res.pick_value == "Chiefs -3"

def test_regex_moneyline(sample_raw_pick):
    sample_raw_pick.raw_text = "Celtics ML -130"
    res = parse_with_regex(sample_raw_pick)
    assert res.bet_type == "Moneyline"