import sys
import os
import pytest
from datetime import date, datetime

# Add root directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import RawPick, ParsedPick

@pytest.fixture
def sample_raw_pick():
    return RawPick(
        id=1,
        source_unique_id="test-123",
        source_url="http://t.me/test/1",
        capper_name="TestCapper",
        raw_text="Lakers -5 -110",
        pick_date=date(2023, 11, 1),
        created_at=datetime.now()
    )

@pytest.fixture
def sample_parsed_pick():
    return ParsedPick(
        raw_pick_id=1,
        league="NBA",
        bet_type="Spread",
        pick_value="Lakers -5",
        unit=1.0,
        odds_american=-110
    )
