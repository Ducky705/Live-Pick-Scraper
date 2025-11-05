"""
SPECIFIC TEST: Capper Name Fix Verification

This test demonstrates that the fix correctly extracts capper names from
aggregator channel messages instead of using the channel name.

BEFORE FIX: capper_name = "FREE CAPPERS PICKS | 🔮" (channel name)
AFTER FIX:  capper_name = "PardonMyPick" (actual capper from message)
"""
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from scrapers import scrape_telegram


class TestCapperNameFix(unittest.TestCase):
    """Test the specific capper name extraction fix."""

    def setUp(self):
        self.patchers = {
            'config': patch('scrapers.config'),
            'client': patch('scrapers.TelegramClient'),
            'upload': patch('scrapers.upload_raw_pick'),
            'session': patch('scrapers.StringSession'),
            'ocr_module': patch.dict('sys.modules', {'pytesseract': None, 'cv2': None, 'numpy': None}),
        }
        self.mocks = {name: p.start() for name, p in self.patchers.items() if name != 'ocr_module'}
        self.mock_client = self.mocks['client'].return_value
        self.mock_client.start, self.mock_client.disconnect = AsyncMock(), AsyncMock()
        self.mock_client.is_connected.return_value = True

        # Configure mock config
        self.mocks['config'].TELEGRAM_API_ID = '12345'
        self.mocks['config'].TELEGRAM_API_HASH = 'abc'
        self.mocks['config'].TELEGRAM_SESSION_NAME = 'test'
        self.mocks['config'].SCRAPE_WINDOW_HOURS = 48
        self.mocks['config'].EASTERN_TIMEZONE = timezone.utc
        self.mocks['config'].PICK_STATUS_PENDING = 'pending'

    def tearDown(self):
        for patcher in self.patchers.values():
            patcher.stop()

    async def run_scraper_with_mock_messages(self, messages, channel_id, channel_title, is_aggregator=False):
        """Helper to run scraper with mocked messages."""
        self.mocks['config'].TELEGRAM_CHANNELS = [channel_id]
        self.mocks['config'].AGGREGATOR_CHANNEL_IDS = {channel_id} if is_aggregator else set()

        mock_entity = MagicMock(id=channel_id, title=channel_title, username=channel_title.lower().replace(' ', ''))
        self.mock_client.get_entity = AsyncMock(return_value=mock_entity)

        mock_message_objects = [
            MagicMock(
                text=text,
                date=datetime.now(timezone.utc),
                photo=None,
                id=idx + 1000
            )
            for idx, text in enumerate(messages)
        ]

        self.mock_client.iter_messages = MagicMock()
        self.mock_client.iter_messages.return_value.__aiter__.return_value = iter(mock_message_objects)

        await scrape_telegram()

    async def test_capper_name_extraction_from_aggregator_channel(self):
        """
        TEST: Verify capper names are extracted from message text, not channel name.

        This tests the exact scenario from the bug report:
        - Channel name: "FREE CAPPERS PICKS | 🔮"
        - Message from aggregator with capper name on first line
        - Should extract the capper name, NOT the channel name
        """
        print("\n" + "="*70)
        print("TEST: Capper Name Extraction from Aggregator Channel")
        print("="*70)

        # Simulate the exact scenario from the bug report
        channel_name = "FREE CAPPERS PICKS | 🔮"
        channel_id = 1900292133  # Aggregator channel ID

        # Messages from aggregator channel with actual capper names
        aggregator_messages = [
            # Format: CapperName\n(empty)\nBet details
            "PardonMyPick\n\n**Lakers ML -110 2u\nWarriors +3 -105 1u**",
            "HammeringHank\n\n**Cowboys ML -130 3u\nGiants +7 -110 1.5u**",
            "PlatinumLocks\n\n**Chiefs -9.5 -115 2u\nOver 48.5 -110 1u**",
            "THE GURU\n\n**Texans ML (1.5U) -130\nColts -3 (1U)**",
            "BETTOR\n\n**Packers (2u) -110\nBears (1.5units) +105**",
        ]

        # Run the scraper
        await self.run_scraper_with_mock_messages(
            aggregator_messages,
            channel_id,
            channel_name,
            is_aggregator=True
        )

        # Verify that upload_raw_pick was called for each message
        assert self.mocks['upload'].call_count == len(aggregator_messages), \
            f"Expected {len(aggregator_messages)} uploads, got {self.mocks['upload'].call_count}"

        # Extract the capper names that were uploaded
        uploaded_capper_names = [
            call[0][0]['capper_name']
            for call in self.mocks['upload'].call_args_list
        ]

        print("\nExpected Capper Names (from message text):")
        expected_names = ["PardonMyPick", "HammeringHank", "PlatinumLocks", "THE GURU", "BETTOR"]
        for name in expected_names:
            print(f"  ✓ {name}")

        print("\nActual Capper Names Extracted:")
        for name in uploaded_capper_names:
            print(f"  ✓ {name}")

        # Verify NONE of them are the channel name
        assert "FREE CAPPERS PICKS" not in str(uploaded_capper_names), \
            "ERROR: Channel name was used as capper name! Fix not working!"

        # Verify all capper names are from the message text
        assert uploaded_capper_names == expected_names, \
            f"Capper names mismatch!\nExpected: {expected_names}\nGot: {uploaded_capper_names}"

        print("\n" + "="*70)
        print("✓ SUCCESS: All capper names extracted correctly from message text!")
        print("✓ Channel name 'FREE CAPPERS PICKS | 🔮' was NOT used")
        print("="*70)

    async def test_channel_name_not_used_as_capper(self):
        """
        TEST: Verify channel name is never used as capper name in aggregator mode.

        This is a regression test to ensure the bug doesn't come back.
        """
        print("\n" + "="*70)
        print("TEST: Regression - Channel Name Should Never Be Capper Name")
        print("="*70)

        channel_name = "FREE CAPPERS PICKS | 🔮"
        channel_id = 1900292133

        # Various message formats from aggregator
        messages = [
            "AnyCapperName\n\n**Pick 1 -110 2u**",
            "AnotherCapper\n\n**Pick 2 -115 1u**",
            "ThirdCapper\n\n**Pick 3 -120 1.5u**",
        ]

        await self.run_scraper_with_mock_messages(
            messages,
            channel_id,
            channel_name,
            is_aggregator=True
        )

        # Get all uploaded capper names
        uploaded_capper_names = [
            call[0][0]['capper_name']
            for call in self.mocks['upload'].call_args_list
        ]

        print("\nUploaded Capper Names:")
        for name in uploaded_capper_names:
            print(f"  ✓ {name}")

        # Verify channel name is NOT in the list
        for capper_name in uploaded_capper_names:
            assert capper_name != channel_name, \
                f"ERROR: Channel name '{channel_name}' was used as capper name!"

        print("\n" + "="*70)
        print("✓ SUCCESS: Channel name correctly excluded from capper names")
        print("="*70)

    async def test_multiple_aggregator_formats(self):
        """
        TEST: Verify fix works for different aggregator message formats.
        """
        print("\n" + "="*70)
        print("TEST: Multiple Aggregator Message Formats")
        print("="*70)

        channel_name = "CAPPERS FREE"
        channel_id = 1900292133

        # Different aggregator message formats
        messages = [
            # Format 1: Capper\n\nPick details
            "SEAN THE KING\n\n**Lakers ML -110 2u**",

            # Format 2: Capper with emoji
            "THIS GIRL BETZ\n\n**🏀76er -5 -110 (2u)**",

            # Format 3: Capper with platform tags
            "BRANDON THE PROFIT\n\n**Texans ML -125 (2U) DK**",

            # Format 4: European decimal units
            "EURO BETTOR\n\n**Barcelona ML -130 2,5u**",
        ]

        expected_capper_names = [
            "SEAN THE KING",
            "THIS GIRL BETZ",
            "BRANDON THE PROFIT",
            "EURO BETTOR"
        ]

        await self.run_scraper_with_mock_messages(
            messages,
            channel_id,
            channel_name,
            is_aggregator=True
        )

        uploaded_capper_names = [
            call[0][0]['capper_name']
            for call in self.mocks['upload'].call_args_list
        ]

        print("\nExpected vs Actual Capper Names:")
        for expected, actual in zip(expected_capper_names, uploaded_capper_names):
            match = "✓" if expected == actual else "✗"
            print(f"  {match} Expected: {expected}")
            print(f"     Actual:   {actual}")

        assert uploaded_capper_names == expected_capper_names, \
            "Capper names don't match expected!"

        print("\n" + "="*70)
        print("✓ SUCCESS: All aggregator formats handled correctly")
        print("="*70)


async def run_capper_name_fix_tests():
    """Run the capper name fix tests."""
    print("\n")
    print("="*70)
    print("CAPPER NAME FIX VERIFICATION TEST SUITE")
    print("="*70)
    print("\nTesting the fix for:")
    print("  Issue: Getting 'FREE CAPPERS PICKS | CRYSTAL BALL' as capper name")
    print("  Fix: Extract actual capper names from message text")
    print("\n")

    suite = unittest.TestLoader().loadTestsFromTestCase(TestCapperNameFix)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*70)
    if result.wasSuccessful():
        print("ALL CAPPER NAME FIX TESTS PASSED!")
        print("The scraper now correctly extracts capper names from messages.")
    else:
        print("SOME TESTS FAILED!")
    print("="*70 + "\n")

    return result.wasSuccessful()


if __name__ == '__main__':
    import asyncio
    asyncio.run(run_capper_name_fix_tests())
