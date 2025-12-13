import pytest
from unittest.mock import MagicMock
from scrapers import TelegramScraper
import config

@pytest.fixture
def scraper(mocker):
    mocker.patch('config.TELEGRAM_API_ID', '123')
    mocker.patch('config.TELEGRAM_API_HASH', 'abc')
    mocker.patch('config.TELEGRAM_SESSION_NAME', 'mock_session')
    mocker.patch('scrapers.StringSession')
    mocker.patch('scrapers.TelegramClient')

    s = TelegramScraper()
    return s

def test_aggregator_capper_extraction(scraper):
    aggregator_id = 1900292133
    config.AGGREGATOR_CHANNEL_IDS = {aggregator_id}
    lines = ["PardonMyPick", "", "Lakers -5"]
    extracted = scraper._extract_capper_name(lines, "FREE CAPPERS PICKS", aggregator_id)
    assert extracted == "PardonMyPick"

def test_non_aggregator_capper_extraction(scraper):
    regular_id = 55555
    config.AGGREGATOR_CHANNEL_IDS = {1900292133}
    lines = ["Lakers -5", "Analysis: Boom."]
    extracted = scraper._extract_capper_name(lines, "Dr Profit Official", regular_id)
    # The logic strips 'Official', so we expect 'Dr Profit'
    assert extracted == "Dr Profit"

def test_blacklist_filtering(scraper):
    regular_id = 55555
    lines = ["Lakers -5"]
    # Input: Gold Boys Free Picks -> Stripped: Gold Boys
    extracted = scraper._extract_capper_name(lines, "Gold Boys Free Picks", regular_id)
    assert extracted == "Gold Boys"
