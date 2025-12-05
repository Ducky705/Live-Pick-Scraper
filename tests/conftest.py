import sys
import os
import pytest
from datetime import date

# Add root directory to python path so tests can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import RawPick

@pytest.fixture
def sample_raw_pick():
    return RawPick(
        id=1,
        source_unique_id="test-123",
        source_url="http://t.me/test/1",
        capper_name="TestCapper",
        raw_text="Lakers -5 -110",
        pick_date=date(2023, 11, 1)
    )