import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from src.parsing.fingerprinter import Fingerprinter
from src.parsing.registry import TemplateRegistry
from src.parsing.learner import Learner

class TestAdaptiveParsing(unittest.TestCase):
    
    def setUp(self):
        self.registry = TemplateRegistry(storage_path="data/test_templates.json")
        self.learner = Learner()
        
    def tearDown(self):
        if os.path.exists("data/test_templates.json"):
            os.remove("data/test_templates.json")
            
    def test_fingerprinting(self):
        # Test basic flow
        text = "Lakers -5 (2u)"
        fp = Fingerprinter.fingerprint(text)
        # Expected: <TEXT> <LINE> (<UNITS>) -> wait, check implementation details
        # Implementation:
        # Lakers -> <TEXT>
        # -5 -> <LINE>
        # (2u) -> <UNITS> replacement?
        # Let's inspect print
        print(f"FP for '{text}': {fp}")
        self.assertIn("<TEXT>", fp)
        self.assertIn("<UNITS>", fp)
        
    def test_learning_cycle(self):
        text = "Lakers -5"
        fp = Fingerprinter.fingerprint(text)
        
        # 1. Check Registry (Should be miss)
        tmpl = self.registry.get_template(fp)
        self.assertIsNone(tmpl)
        
        # 2. Learn
        result = self.learner.learn_format(text)
        self.assertIsNotNone(result)
        regex, mapping = result
        
        # 3. Register
        self.registry.register_template(fp, regex, mapping, example=text)
        
        # 4. Check Registry (Should be hit)
        hit_tmpl = self.registry.get_template(fp)
        self.assertIsNotNone(hit_tmpl)
        pattern, map_out = hit_tmpl
        
    def test_integration(self):
        # 1. Register a template directly
        text = "Celtics -3"
        fp = Fingerprinter.fingerprint(text)
        regex = r"^(?P<selection>[a-zA-Z\s]+)\s+(?P<line>[+-]?\d+(?:\.\d+)?)$"
        mapping = {"selection": "selection", "line": "line"}
        
        self.registry.register_template(fp, regex, mapping)
        
        # 2. Call PickParser
        from src.grading.parser import PickParser
        pick = PickParser.parse(text, league="NBA")
        
        # 3. Verify it used the template
        self.assertEqual(pick.selection.strip(), "Celtics")
        self.assertEqual(pick.line, -3.0)
        self.assertEqual(pick.bet_type.value, "Spread")

if __name__ == "__main__":
    unittest.main()
