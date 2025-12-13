import pytest
from unittest.mock import MagicMock
from scrapers import TelegramScraper
import config

@pytest.fixture
def scraper(mocker):
    mocker.patch('config.TELEGRAM_API_ID', '123')
    mocker.patch('config.TELEGRAM_API_HASH', 'abc')
    mocker.patch('config.TELEGRAM_SESSION_NAME', 'mock')
    mocker.patch('scrapers.TelegramClient')
    mocker.patch('scrapers.StringSession')
    return TelegramScraper()

def test_is_valid_pick_message(scraper):
    assert scraper._is_valid_pick_message("Lakers -5") is True
    assert scraper._is_valid_pick_message("Loss ❌") is False

def test_extract_capper_name(scraper):
    # Case 1: Capper name found in body (Aggregator behavior)
    config.AGGREGATOR_CHANNEL_IDS = {123}
    
    lines = ["Test Capper", "Lakers -5"]
    name = scraper._extract_capper_name(lines, "Aggregator Channel", 123)
    assert name == "Test Capper"

def test_extract_capper_name_fallback(scraper):
    # Case 2: No name in body, falls back to channel title
    config.AGGREGATOR_CHANNEL_IDS = set() # Reset
    lines = ["Lakers -5"]
    
    # "Main Channel" is used because "Source Channel" would trigger 
    # the regex that strips 'Source:' prefixes.
    name = scraper._extract_capper_name(lines, "Main Channel", 456)
    assert name == "Main Channel"

def test_extract_capper_name_cleaning(scraper):
    # Case 3: "Gold Boys Free Picks" -> "Gold Boys"
    lines = ["Lakers -5"]
    name = scraper._extract_capper_name(lines, "Gold Boys Free Picks", 789)
    assert name == "Gold Boys"
