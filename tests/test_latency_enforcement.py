import logging
import unittest
from unittest.mock import patch

import requests

from src.parallel_batch_processor import ParallelBatchProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)


class TestLatencyEnforcement(unittest.TestCase):
    def setUp(self):
        self.processor = ParallelBatchProcessor(providers=["groq", "mistral"])

    def test_tier1_timeout_config(self):
        """Test that Tier 1 provider (Groq) receives 15.0s timeout."""
        print("\nTesting Tier 1 (Groq) Timeout Config...")
        with patch("src.parallel_batch_processor.groq_text_completion") as mock_groq:
            mock_groq.return_value = "Success"

            batch = [{"id": 1, "text": "test"}]
            try:
                self.processor._execute_request("groq", batch)
            except Exception as e:
                print(f"Exception: {e}")

            args, kwargs = mock_groq.call_args
            print(f"Groq called with: {kwargs}")
            self.assertEqual(kwargs.get("timeout"), 15.0, "Tier 1 should have 15.0s timeout")

    def test_tier2_timeout_config(self):
        """Test that Tier 2 provider (Mistral) receives 25.0s timeout."""
        print("\nTesting Tier 2 (Mistral) Timeout Config...")
        with patch("src.parallel_batch_processor.mistral_completion") as mock_mistral:
            mock_mistral.return_value = "Success"

            batch = [{"id": 1, "text": "test"}]
            try:
                self.processor._execute_request("mistral", batch)
            except Exception as e:
                print(f"Exception: {e}")

            args, kwargs = mock_mistral.call_args
            print(f"Mistral called with: {kwargs}")
            self.assertEqual(kwargs.get("timeout"), 25.0, "Tier 2 should have 25.0s timeout")

    def test_timeout_logging_and_reraise(self):
        """Test that Timeout exceptions are caught, logged as 'Timeout Failure', and re-raised."""
        print("\nTesting Timeout Logging...")
        with patch("src.parallel_batch_processor.groq_text_completion") as mock_groq:
            # Simulate Timeout
            mock_groq.side_effect = requests.exceptions.Timeout("Mock Timeout")

            batch = [{"id": 1, "text": "test"}]

            with self.assertLogs(logger="src.parallel_batch_processor", level="ERROR") as cm:
                with self.assertRaises(requests.exceptions.Timeout):
                    self.processor._execute_request("groq", batch)

                print(f"Logs captured: {cm.output}")
                has_timeout_log = any("Timeout Failure" in o for o in cm.output)
                self.assertTrue(has_timeout_log, "Should log 'Timeout Failure'")


if __name__ == "__main__":
    unittest.main()
