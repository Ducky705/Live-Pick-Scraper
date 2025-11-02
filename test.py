# File: ./test.py
import asyncio
import unittest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone

# --- Modules to be tested ---
from scrapers import scrape_telegram
from ai_parser import parse_with_ai
from processing_service import run_processor
from simple_parser import parse_with_regex
from standardizer import clean_unit_value
from config import BET_TYPE_STANDARDS

# --- Data fixtures from the provided JSON for realistic testing ---
REAL_WORLD_MESSAGES = {
    "multi_pick_card": "CASH CING\n\n**2.5u, Texans ML -130\n2u, Chiefs ML -130\n1,5u, Seahawks -3 -110**",
    "leading_emoji": "THIS GIRL BETZ\n\n**🏀76er -5 -110 (2u)\n🏀Hornets -120 (2u)**",
    "parenthetical_units": "THE GURU\n\n**Texans ML (1.5U) -130\nColts -3 (1U)**",
    "ambiguous_parlay": "BRANDON THE PROFIT\n\n**Jefferson (Vikings)\nWarren (Steelers)\nTD Parlay (0.25U) FD**",
    "complex_game_card": "SEEKING RETURNS\n\n**4:05PM NFL: Saints Vs. Rams\nPicks:\nNO LA Under 44.5 -112 5U (FD)\nNO TTU 14.5 -111 3U (FD)**",
    "ambiguous_single_line": "BETTING WITH BUSH\n\n**NFL\n\nFalcons +12  Raiders +8.5 -120 1.5u**",
    "simple_player_prop": "ANDERS PICKS\n\n**NFL\nBrashard Smith o4.5 Carries +105 1U(mgm)**"
}

# --- Test Case for the Simple Regex Parser ---
class TestSimpleParser(unittest.TestCase):
    """Focuses on testing the fast, regex-based parser against real-world formats."""

    def test_parses_simple_moneyline_with_parentheses(self):
        raw_pick = {'id': 101, 'raw_text': 'Texans ML (-130) 1.5u'}
        result = parse_with_regex(raw_pick)
        self.assertIsNotNone(result)
        self.assertEqual(result['bet_type'], 'Moneyline')
        self.assertEqual(result['pick_value'], 'Texans ML')
        self.assertEqual(result['odds_american'], -130)
        self.assertEqual(result['unit'], 1.5)

    def test_parses_line_with_leading_emoji(self):
        raw_pick = {'id': 102, 'raw_text': '🏀76er -5 -110 (2u)'}
        result = parse_with_regex(raw_pick)
        self.assertIsNone(result, "Simple parser should not handle leading emojis, but it did.")
        
    def test_REJECTS_multi_pick_cards(self):
        raw_pick = {'id': 103, 'raw_text': REAL_WORLD_MESSAGES["multi_pick_card"]}
        result = parse_with_regex(raw_pick)
        self.assertIsNone(result, "Simple parser incorrectly handled a multi-pick card.")

# --- Test Case for Telegram Scraper ---
class TestTelegramScraper(unittest.IsolatedAsyncioTestCase):
    """Focuses on raw message ingestion and cleaning."""

    def setUp(self):
        self.patchers = {
            'config': patch('scrapers.config'),
            'client': patch('scrapers.TelegramClient'),
            'upload': patch('scrapers.upload_raw_pick'),
            'session': patch('scrapers.StringSession')
        }
        self.mocks = {name: p.start() for name, p in self.patchers.items()}
        self.mock_client = self.mocks['client'].return_value
        self.mock_client.start, self.mock_client.disconnect = AsyncMock(), AsyncMock()
        self.mock_client.is_connected.return_value = True
        self.mocks['config'].TELEGRAM_API_ID, self.mocks['config'].TELEGRAM_API_HASH, self.mocks['config'].TELEGRAM_SESSION_NAME = '12345', 'abc', 'test'
        self.mocks['config'].SCRAPE_WINDOW_HOURS, self.mocks['config'].EASTERN_TIMEZONE, self.mocks['config'].PICK_STATUS_PENDING = 1, timezone.utc, 'pending'

    def tearDown(self):
        patch.stopall()

    async def run_scraper_with_mock_messages(self, messages, channel_id, channel_title, is_aggregator=False):
        self.mocks['config'].TELEGRAM_CHANNELS = [channel_id]
        self.mocks['config'].AGGREGATOR_CHANNEL_IDS = {channel_id} if is_aggregator else set()
        mock_entity = MagicMock(id=channel_id, title=channel_title)
        self.mock_client.get_entity = AsyncMock(return_value=mock_entity)
        mock_message_objects = [MagicMock(text=text, date=datetime.now(timezone.utc), photo=None) for text in messages]
        self.mock_client.iter_messages.return_value = MagicMock()
        self.mock_client.iter_messages.return_value.__aiter__.return_value = iter(mock_message_objects)
        await scrape_telegram()

    async def test_scraper_cleans_complex_card(self):
        message = REAL_WORLD_MESSAGES["multi_pick_card"] + "\n\n➖➖➖➖➖\nDM ME"
        await self.run_scraper_with_mock_messages([message], 1900292133, 'CAPPERS FREE🚨', is_aggregator=True)
        self.mocks['upload'].assert_called_once()
        uploaded_data = self.mocks['upload'].call_args[0][0]
        self.assertEqual(uploaded_data['capper_name'], 'CASH CING')
        self.assertEqual(uploaded_data['raw_text'], "**2.5u, Texans ML -130\n2u, Chiefs ML -130\n1,5u, Seahawks -3 -110**")

    async def test_skips_malformed_aggregator_message(self):
        """
        Ensures a message in an aggregator channel WITHOUT a capper name is SKIPPED,
        preventing the channel name ('CAPPERS FREE🚨') from being used as the capper.
        """
        malformed_message = "**2.5u, Texans ML -130\n2u, Chiefs ML -130**\n\n➖➖➖➖➖\nDM ME"
        await self.run_scraper_with_mock_messages([malformed_message], 1900292133, 'CAPPERS FREE🚨', is_aggregator=True)
        self.mocks['upload'].assert_not_called()

# --- Test Case for Full Processing Service Integration ---
class TestProcessingService(unittest.TestCase):
    """An integration-style test for the entire processing flow."""

    @patch('processing_service.insert_structured_picks')
    @patch('processing_service.update_raw_picks_status')
    @patch('processing_service.get_or_create_capper')
    @patch('processing_service.parse_with_ai')
    @patch('processing_service.get_pending_raw_picks')
    def test_full_pipeline_with_real_world_data(self, mock_get_pending, mock_parse_ai, mock_get_capper, mock_update, mock_insert):
        mock_get_pending.return_value = [
            {'id': 1, 'raw_text': 'Texans ML -122 1u', 'capper_name': 'BETTING WITH BUSH', 'pick_date': '2025-11-02', 'source_url': 'url1', 'source_unique_id': 'id1'},
            {'id': 2, 'raw_text': REAL_WORLD_MESSAGES["complex_game_card"], 'capper_name': 'SEEKING RETURNS', 'pick_date': '2025-11-02', 'source_url': 'url2', 'source_unique_id': 'id2'},
            {'id': 3, 'raw_text': '🏀Spurs -5.5 -110 (3u)', 'capper_name': 'THIS GIRL BETZ', 'pick_date': '2025-11-02', 'source_url': 'url3', 'source_unique_id': 'id3'},
        ]
        
        mock_parse_ai.return_value = [
            {'raw_pick_id': 2, 'league': 'NFL', 'bet_type': 'Parlay', 'pick_value': 'Complex Parlay Details', 'unit': 1.0},
            {'raw_pick_id': 3, 'league': 'NBA', 'bet_type': 'Spread', 'pick_value': 'San Antonio Spurs -5.5', 'unit': 3.0}
        ]
        
        mock_get_capper.side_effect = [10, 11, 12] 

        run_processor()

        mock_parse_ai.assert_called_once()
        ai_call_args = mock_parse_ai.call_args[0][0]
        self.assertEqual(len(ai_call_args), 2)
        self.assertEqual({p['raw_pick_id'] for p in ai_call_args}, {2, 3})

        mock_insert.assert_called_once()
        inserted_data = mock_insert.call_args[0][0]
        self.assertEqual(len(inserted_data), 3)

        mock_update.assert_called_once()
        processed_ids = set(mock_update.call_args[0][0])
        self.assertEqual(processed_ids, {1, 2, 3})

if __name__ == '__main__':
    unittest.main()