import pytest
import json
import glob
import os
from datetime import date
from models import RawPick
from simple_parser import parse_with_regex
from ai_parser import parse_with_ai

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
JSON_FILES = glob.glob(os.path.join(ROOT_DIR, "telegram_debug_data_*.json"))

ALL_MESSAGES = []
for fpath in JSON_FILES:
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                ALL_MESSAGES.extend(data)
    except Exception as e:
        print(f"Skipping file {fpath}: {e}")

if not ALL_MESSAGES:
    ALL_MESSAGES = [{"text": "Lakers -5", "id": 999, "channel_name": "Test"}]

@pytest.mark.parametrize("msg_data", ALL_MESSAGES[:50])
def test_historical_parsing_stability(msg_data):
    text = msg_data.get('text', '') or ""
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

    try:
        regex_results = parse_with_regex(pick)
        if regex_results:
            assert regex_results[0].pick_value is not None
            assert regex_results[0].bet_type in ["Spread", "Total", "Moneyline"]
    except Exception as e:
        pytest.fail(f"Regex Parser CRASHED on message ID {pick.id}: {e}")
