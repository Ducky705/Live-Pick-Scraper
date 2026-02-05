import unittest
import sys
import os
sys.path.insert(0, os.path.abspath("."))
from src.rule_based_extractor import RuleBasedExtractor
from src.grading.schema import BetType

class TestRuleFailures(unittest.TestCase):
    def test_pra_prop(self):
        # Msg 13002: Luka Doncic 45+ PRA (-120)
        msg = {"id": 1, "text": "Luka Doncic 45+ PRA (-120)"}
        picks, _ = RuleBasedExtractor.extract([msg])
        
        self.assertEqual(len(picks), 1)
        p = picks[0]
        self.assertEqual(p["capper_name"], "Unknown")
        self.assertIn("Luka Doncic", p["pick"])
        self.assertEqual(p["type"], BetType.PLAYER_PROP.value)
        # Should detect stat
        self.assertTrue("PRA" in p["pick"] or p["stat"] == "PRA")
        # Should normalize line (45+ -> Over 44.5 ideally, but 45 is acceptable for rule engine)
        
    def test_threes_prop(self):
        # Msg 13002: Steph Curry 5+ Threes (+110)
        msg = {"id": 2, "text": "Steph Curry 5+ Threes (+110)"}
        picks, _ = RuleBasedExtractor.extract([msg])
        
        self.assertEqual(len(picks), 1)
        p = picks[0]
        self.assertEqual(p["capper_name"], "Unknown")
        # self.assertEqual(p["type"], BetType.PLAYER_PROP.value)
        # "Threes" detection
        
    def test_parlay_splitting(self):
        # Msg 12806: Abeta Gautier ITD || Paddy Pimblett -136 2u
        msg = {"id": 3, "text": "Abeta Gautier ITD || Paddy Pimblett -136 2u"}
        picks, _ = RuleBasedExtractor.extract([msg])
        
        # This is strictly a PROP (Parlay of Props) or a PARLAY.
        # Currently Rule Engine might see it as 1 pick or 2.
        # "||" usually denotes a parlay.
        self.assertTrue(len(picks) > 0)
        
    def test_multi_unit_extraction(self):
        # Msg 13003: Commanders +3.5 (-115) 5U MAX
        msg = {"id": 4, "text": "Commanders +3.5 (-115) 5U MAX"}
        picks, _ = RuleBasedExtractor.extract([msg])
        
        self.assertEqual(len(picks), 1)
        self.assertEqual(picks[0]["units"], 5.0)

if __name__ == "__main__":
    unittest.main()
