import unittest
import json
from src.prompts.decoder import normalize_response


class TestHallucinationPrevention(unittest.TestCase):
    def test_odds_stripping(self):
        """
        Test that odds NOT present in the source text are stripped.
        """
        # Source text has NO odds (just "Lakers to win")
        message_id = 123
        source_text = "Lakers to win tonight vs Warriors."

        # Context map
        context = {message_id: source_text}

        # AI hallucinates -110 odds
        # Use valid JSON string format
        ai_response = json.dumps(
            [{"i": 123, "p": "Lakers", "t": "Moneyline", "o": -110}]
        )

        # Run normalization with context
        results = normalize_response(ai_response, expand=True, message_context=context)

        # Check result
        pick = results[0]
        print(f"\nSource: '{source_text}'")
        print(f"AI Output: {ai_response}")
        print(f"Result Odds: {pick.get('odds')}")

        # Assert odds were stripped
        self.assertIsNone(
            pick.get("odds"),
            "Hallucinated odds (-110) should have been removed because they are not in text.",
        )

    def test_odds_keeping(self):
        """
        Test that odds PRESENT in the source text are kept.
        """
        message_id = 456
        source_text = "Lakers -110 to win."
        context = {message_id: source_text}

        ai_response = json.dumps(
            [{"i": 456, "p": "Lakers", "t": "Moneyline", "o": -110}]
        )

        results = normalize_response(ai_response, expand=True, message_context=context)
        pick = results[0]

        print(f"\nSource: '{source_text}'")
        print(f"Result Odds: {pick.get('odds')}")

        # Assert odds were KEPT
        self.assertEqual(
            pick.get("odds"), -110, "Valid odds (-110) should have been kept."
        )


if __name__ == "__main__":
    unittest.main()
