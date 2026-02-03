import logging
import unittest
from unittest.mock import patch
from src.parallel_batch_processor import ParallelBatchProcessor, PROVIDER_CONFIG

# Configure logging to avoid spam during tests
logging.basicConfig(level=logging.CRITICAL)


class TestParallelBatchProcessorConfig(unittest.TestCase):
    def setUp(self):
        self.processor = ParallelBatchProcessor(providers=["chimera"])

    def test_chimera_config_exists(self):
        """Verify Chimera provider configuration matches requirements."""
        self.assertIn("chimera", PROVIDER_CONFIG)
        config = PROVIDER_CONFIG["chimera"]
        self.assertEqual(config["model"], "tngtech/deepseek-r1t2-chimera:free")
        self.assertEqual(config["rpm"], 10)
        self.assertEqual(config["tpm"], 100000)
        self.assertEqual(config["max_concurrent"], 2)
        self.assertEqual(config["priority"], 1)

    @patch("src.parallel_batch_processor.openrouter_completion")
    def test_chimera_execution_path(self, mock_completion):
        """Verify Chimera requests are routed to OpenRouter client."""
        mock_completion.return_value = "Success"

        # Messages structure expected by generate_ai_prompt
        messages = [{"id": 123, "text": "Lakers -5", "ocr_texts": []}]
        result = self.processor._execute_request("chimera", messages)

        self.assertEqual(result, "Success")

        # Verify openrouter_completion was called with correct model
        mock_completion.assert_called_once()
        args, kwargs = mock_completion.call_args
        self.assertEqual(kwargs["model"], "tngtech/deepseek-r1t2-chimera:free")


if __name__ == "__main__":
    unittest.main()
