import pytest
from simple_parser import parse_with_regex, _stitch_lines, _clean_hype_text, _is_valid_team_name
from models import RawPick
from datetime import date

def test_hype_cleaning():
    text = "🔥 WHALE PLAY MAX BET Lakers -5 💰"
    clean = _clean_hype_text(text)
    assert "Lakers -5" in clean

def test_ocr_artifact_cleaning():
    text = "©) Over 210 | ]"
    clean = _clean_hype_text(text)
    assert "Over 210" in clean
    assert "©" not in clean

def test_line_stitching():
    lines = ["Los Angeles Lakers", "-5 -110"]
    stitched = _stitch_lines(lines)
    assert len(stitched) == 1
    assert stitched[0] == "Los Angeles Lakers -5 -110"

def test_parse_spread(sample_raw_pick):
    sample_raw_pick.raw_text = "Lakers -5 -110"
    results = parse_with_regex(sample_raw_pick)
    assert len(results) == 1
    assert results[0].bet_type == "Spread"
    assert results[0].pick_value == "Lakers -5"

def test_deduplication(sample_raw_pick):
    # OCR often repeats text
    sample_raw_pick.raw_text = "Lakers -5\nLakers -5\nLakers -5"
    results = parse_with_regex(sample_raw_pick)
    # Should only return 1 pick
    assert len(results) == 1
    assert results[0].pick_value == "Lakers -5"

def test_invalid_team_names():
    assert _is_valid_team_name("Lakers") is True
    assert _is_valid_team_name("points per game.") is False
    assert _is_valid_team_name("analysis:") is False
    assert _is_valid_team_name("cappers") is False
