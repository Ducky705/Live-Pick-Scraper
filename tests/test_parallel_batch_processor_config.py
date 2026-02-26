import logging
import unittest
from unittest.mock import patch
from src.parallel_batch_processor import ParallelBatchProcessor, PROVIDER_CONFIG

# Configure logging to avoid spam during tests
logging.basicConfig(level=logging.CRITICAL)


class TestParallelBatchProcessorConfig(unittest.TestCase):
    def setUp(self):
        self.processor = ParallelBatchProcessor(providers=["openrouter"])

    def test_openrouter_config_exists(self):
        """Verify OpenRouter provider configuration matches requirements."""
        self.assertIn("openrouter", PROVIDER_CONFIG)
        config = PROVIDER_CONFIG["openrouter"]
        self.assertEqual(config["model"], "stepfun/step-3.5-flash:free")
        self.assertEqual(config["rpm"], 10)
        self.assertEqual(config["tpm"], 100000)
        self.assertEqual(config["max_concurrent"], 5)
        self.assertEqual(config["priority"], 0)

    @patch("src.parallel_batch_processor.openrouter_completion")
    def test_openrouter_execution_path(self, mock_completion):
        """Verify OpenRouter requests are routed to OpenRouter client."""
        mock_completion.return_value = "Success"

        # Messages structure expected by generate_ai_prompt
        messages = [{"id": 123, "text": "Lakers -5", "ocr_texts": []}]
        result = self.processor._execute_request("openrouter", messages)

        self.assertEqual(result, "Success")

        # Verify openrouter_completion was called with correct model
        mock_completion.assert_called_once()
        args, kwargs = mock_completion.call_args
        self.assertEqual(kwargs["model"], "stepfun/step-3.5-flash:free")


if __name__ == "__main__":
    unittest.main()
