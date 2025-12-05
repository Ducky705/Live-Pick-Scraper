import pytest
from unittest.mock import MagicMock
from scrapers import TelegramScraper

@pytest.fixture
def scraper(mocker):
    # Mock everything needed for instantiation
    mocker.patch('config.TELEGRAM_API_ID', '123')
    mocker.patch('config.TELEGRAM_API_HASH', 'abc')
    mocker.patch('config.TELEGRAM_SESSION_NAME', 'mock')
    mocker.patch('scrapers.StringSession')
    mocker.patch('scrapers.TelegramClient')
    return TelegramScraper()

def test_extract_capper_name_normal(scraper):
    lines = ["Dr. Profit", "", "Lakers -5"]
    assert scraper._extract_capper_name(lines, "Agg Channel", 9999) == "Dr. Profit"

def test_extract_capper_name_hype(scraper):
    lines = ["WHALE PLAY", "", "Lakers -5"]
    assert scraper._extract_capper_name(lines, "My Channel", 9999) == "My Channel"

    lines = ["MAX BET", "Lakers -5"]
    assert scraper._extract_capper_name(lines, "My Channel", 9999) == "My Channel"

def test_is_valid_pick_message(scraper):
    # Valid
    assert scraper._is_valid_pick_message("Lakers -5") is True
    
    # Valid (Checkmark is allowed now, as it appears in channel names/hype)
    assert scraper._is_valid_pick_message("Lakers -5 ✅") is True
    
    # Invalid (Explicit Loss/Result indicators)
    assert scraper._is_valid_pick_message("Lakers -5 LOSS") is False
    assert scraper._is_valid_pick_message("Lakers -5 ❌") is False