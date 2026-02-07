
import sys
import os
import json
import logging

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# Disable AI
from src.grading.ai_resolver import AIResolver
AIResolver.resolve_pick = lambda text, league, scores: None

from src.grading.parser import PickParser
from src.grading.engine import GraderEngine

FIXTURE_PATH = "tests/fixtures/goldenset_scores.json"

def main():
    with open(FIXTURE_PATH) as f:
        scores = json.load(f)
        
    engine = GraderEngine(scores)
    
    pick_text = "1Q Spurs -1.5 **"
    parsed = PickParser.parse(pick_text)
    print(f"Parsed League: {parsed.league}")
    print(f"Parsed Period: {parsed.period}")
    
    graded = engine.grade(parsed)
    print(f"Grade: {graded.grade}")
    print(f"Summary: {graded.score_summary}")
    print(f"Details: {graded.details}")

if __name__ == "__main__":
    main()
