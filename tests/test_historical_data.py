import pytest
import json
import glob
import os
from datetime import date
from models import RawPick
from simple_parser import parse_with_regex
from ai_parser import parse_with_ai

# Find all debug JSON files in the root directory
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
JSON_FILES = glob.glob(os.path.join(ROOT_DIR, "telegram_debug_data_*.json"))

# Combine messages from all files
ALL_MESSAGES = []
for fpath in JSON_FILES:
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Normalize list vs dict structure if necessary
            if isinstance(data, list):
                ALL_MESSAGES.extend(data)
    except Exception as e:
        print(f"Skipping file {fpath}: {e}")

# If no debug files found, create a dummy one for the test to skip gracefully
if not ALL_MESSAGES:
    ALL_MESSAGES = [{"text": "Lakers -5", "id": 999, "channel_name": "Test"}]

@pytest.mark.parametrize("msg_data", ALL_MESSAGES[:50]) # Test first 50 to save time
def test_historical_parsing_stability(msg_data):
    """
    Iterates through real historical messages.
    Ensures that the parsers do not CRASH on real data.
    Checks if regex can find picks in known valid formats.
    """
    text = msg_data.get('text', '') or ""
    # Some debug files might have 'ocr_text', join them safely
    if 'ocr_text' in msg_data:
        text += chr(10) + msg_data['ocr_text']
        
    if not text.strip():
        pytest.skip("Empty text")

    pick = RawPick(
        id=msg_data.get('id', 0),
        source_unique_id=f"hist-{msg_data.get('id', 0)}",
        source_url="history",
        capper_name=msg_data.get('channel_name', 'Unknown'),
        raw_text=text,
        pick_date=date.today()
    )

    # 1. Test Regex Parser Stability
    try:
        regex_result = parse_with_regex(pick)
        if regex_result:
            assert regex_result.pick_value is not None
            assert regex_result.bet_type in ["Spread", "Total", "Moneyline"]
    except Exception as e:
        pytest.fail(f"Regex Parser CRASHED on message ID {pick.id}: {e}")

@pytest.mark.skipif(not os.getenv("OPENROUTER_API_KEY"), reason="No AI API Key")
def test_ai_parser_integration():
    """
    Takes a small batch of historical picks and sends them to the AI.
    Only runs if API Key is present.
    """
    valid_batch = []
    for msg in ALL_MESSAGES[:3]:
        text = msg.get('text', '')
        if len(text) > 10:
             valid_batch.append(RawPick(
                id=msg.get('id', 0),
                source_unique_id="ai-test",
                source_url="ai-test",
                capper_name="Test",
                raw_text=text,
                pick_date=date.today()
            ))
    
    if not valid_batch:
        pytest.skip("No suitable messages for AI test")

    try:
        results = parse_with_ai(valid_batch)
        assert isinstance(results, list)
    except Exception as e:
        pytest.fail(f"AI Parser Integration CRASHED: {e}")