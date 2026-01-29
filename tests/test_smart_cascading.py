import unittest
from unittest.mock import patch

from src.parallel_batch_processor import (
    ComplexityRouter,
    ParallelBatchProcessor,
)


class TestSmartCascading(unittest.TestCase):
    def setUp(self):
        self.processor = ParallelBatchProcessor()

    def test_complexity_router_text(self):
        """Tier 1: Simple text"""
        batch = [{"id": 1, "text": "Simple bet"}]
        routing = ComplexityRouter.analyze_batch(batch)
        self.assertEqual(routing["tier"], 1)

    def test_complexity_router_complex(self):
        """Tier 2: Long text"""
        batch = [{"id": 1, "text": "A" * 3001}]
        routing = ComplexityRouter.analyze_batch(batch)
        self.assertEqual(routing["tier"], 2)

    def test_complexity_router_vision(self):
        """Tier 2: Image"""
        batch = [{"id": 1, "text": "Hi", "image": "path/to/img.jpg"}]
        routing = ComplexityRouter.analyze_batch(batch)
        self.assertEqual(routing["tier"], 2)

    @patch("src.parallel_batch_processor.gemini_text_completion")
    def test_tier_1_success(self, mock_gemini):
        """Verify routing to Tier 1 (Gemini)"""
        mock_gemini.return_value = "Result"
        # Correct format: List of lists of dicts
        batch = [[{"id": 1, "text": "Simple"}]]

        results = self.processor.process_batches(batch)
        self.assertEqual(len(results), 1)
        self.assertEqual(self.processor.stats["gemini"]["count"], 1)

    @patch("src.parallel_batch_processor.gemini_text_completion")
    @patch("src.parallel_batch_processor.cerebras_completion")
    @patch("src.parallel_batch_processor.groq_text_completion")
    def test_escalation(self, mock_groq, mock_cerebras, mock_gemini):
        """Verify escalation Tier 1 -> Tier 2 on failure"""
        # Tier 1 fails
        mock_gemini.side_effect = Exception("Rate Limit 429")
        mock_cerebras.side_effect = Exception("Error")
        # Tier 2 succeeds
        mock_groq.return_value = "Recovered"

        batch = [[{"id": 1, "text": "Simple"}]]
        results = self.processor.process_batches(batch)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], "Recovered")
        # Ensure stats reflect this
        self.assertEqual(self.processor.stats["groq"]["count"], 1)
        self.assertGreater(self.processor.circuit_breaker.errors["gemini"], 0)


if __name__ == "__main__":
    unittest.main()
