
import sys
import os
import json
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import detect_common_watermark, clean_text_for_ai
from src.grader import grade_picks
from src.prompt_builder import generate_revision_prompt

class TestProductionFeatures(unittest.TestCase):
    
    def test_watermark_detection(self):
        print("\n--- Testing Watermark Detection ---")
        # Test case 1: Common watermark (needs >1 occurrence and @/dm/join keyword in strict mode)
        texts = ["Pick 1\n@cappersfree", "Pick 2\n@cappersfree", "Another pick"]
        detected = detect_common_watermark(texts)
        print(f"Texts: {texts} -> Detected: {detected}")
        self.assertIn("@cappersfree", detected)
        
        # Test case 2: No watermark
        texts = ["Just text", "No watermark here"]
        detected = detect_common_watermark(texts)
        print(f"Texts: {texts} -> Detected: {detected}")
        self.assertEqual(detected, "")
        
        # Test case 3: Threshold check (needs > 5 messages usually, but logic might vary)
        # Looking at utils.py logic: likely frequency based.
    
    def test_grading_logic(self):
        print("\n--- Testing Grading Logic ---")
        scores = [
            {"team1": "Lakers", "score1": 110, "team2": "Celtics", "score2": 100, "league": "NBA", "date": "2024-01-01"},
            {"team1": "Chiefs", "score1": 24, "team2": "Bills", "score2": 21, "league": "NFL", "date": "2024-01-01"}
        ]
        
        picks = [
            {"message_id": "1", "pick": "Lakers -5", "league": "NBA", "date": "2024-01-01"},
            {"message_id": "2", "pick": "Celtics ML", "league": "NBA", "date": "2024-01-01"},
            {"message_id": "3", "pick": "Bills +3.5", "league": "NFL", "date": "2024-01-01"},
            {"message_id": "4", "pick": "Over 200", "league": "NBA", "date": "2024-01-01"} # Simple Over check
        ]
        
        # We need to see if grade_picks can handle these.
        # Note: grade_picks implementation details might require specific formats.
        # Assuming grade_picks takes (picks, scores).
        
        results = grade_picks(picks, scores)
        
        for r in results:
            print(f"Pick: {r['pick']} -> Result: {r.get('result')} (Score: {r.get('score_summary')})")
            
        # Lakers -5 (110-100 = 10 diff) -> Win
        self.assertEqual(next(p for p in results if p['message_id'] == '1')['result'], 'Win')
        # Celtics ML (Lost) -> Loss
        self.assertEqual(next(p for p in results if p['message_id'] == '2')['result'], 'Loss')
        
    def test_refinery_prompt_builder(self):
        print("\n--- Testing Refinery Prompt Builder ---")
        failed_items = [
            {"message_id": "1", "capper_name": "Unknown", "league": "Unknown", "pick": "Lakers", "original_text": "Lakers game tonight"}
        ]
        prompt = generate_revision_prompt(failed_items)
        print("Generated Revision Prompt length:", len(prompt))
        self.assertIn("Lakers game tonight", prompt)
        self.assertIn("Unknown", prompt)

if __name__ == '__main__':
    unittest.main()
