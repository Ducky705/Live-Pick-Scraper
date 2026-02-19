# Add project root to path
# (Assuming script is run from project root, but need to be safe)
import os, sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")

sys.path.insert(0, os.path.abspath("."))

from src.grading.parser import PickParser
from src.grading.engine import GraderEngine
HARD_MODE_PICKS = [
    # Natural Language
    {"text": "I really like the Lakers to win tonight", "expected_type": "Moneyline", "selection": "Lakers", "league": "NBA"},
    {"text": "Give me the Chiefs covering the spread", "expected_type": "Spread", "selection": "Chiefs", "league": "NFL"},
    {"text": "Hammer the over in the Celtics game", "expected_type": "Total", "is_over": True, "league": "NBA"},
    
    # Typos & Loose Formats
    {"text": "Lakerss -5", "expected_type": "Spread", "selection": "Lakers", "league": "NBA"},
    {"text": "Warriors ML", "expected_type": "Moneyline", "selection": "Warriors", "league": "NBA"},
    {"text": "Knicks vs Nets O 220", "expected_type": "Total", "is_over": True, "league": "NBA"},
    
    # Complex/Implied
    {"text": "LeBron 25+ points", "expected_type": "Player Prop", "stat": "points", "line": 25, "league": "NBA"},
    {"text": "Mahomes 300+ yards passing", "expected_type": "Player Prop", "stat": "pass yards", "line": 300, "league": "NFL"},
    
    # No Separators / Run-on
    {"text": "Lakers -5 Celtics ML", "expected_type": "Parlay", "legs_count": 2, "league": "NBA"},
    {"text": "Bills -3 Chiefs Over 48", "expected_type": "Parlay", "legs_count": 2, "league": "NFL"},
]

def run_benchmark():
    print("="*60)
    print("HARD MODE GRADING BENCHMARK")
    print("="*60)
    
    passed = 0
    total = len(HARD_MODE_PICKS)
    
    engine = GraderEngine([])

    for case in HARD_MODE_PICKS:
        text = case["text"]
        league = case.get("league", "Unknown")
        expected_type = case["expected_type"]
        
        print(f"\nTesting: '{text}'")
        
        # 1. Parsing via Engine (to trigger AI fallback)
        try:
            # We don't care about the grade result (WIN/LOSS), only the parsing
            graded = engine.grade(text, league)
            parsed = graded.pick
            
            print(f"  -> Parsed Type: {parsed.bet_type.value}")
            print(f"  -> Selection: '{parsed.selection}' (Len: {len(parsed.selection.split())})")
            if parsed.legs:
                print(f"  -> Legs: {len(parsed.legs)}")
                for i, leg in enumerate(parsed.legs):
                    print(f"    - Leg {i+1}: {leg.bet_type.value} | {leg.selection} | Line: {leg.line}")
            
            # Validity Check
            is_match = False
            if parsed.bet_type.value == expected_type:
                is_match = True
                
            # Deep Check
            if is_match and "selection" in case:
                if case["selection"].lower() not in parsed.selection.lower():
                     print(f"     Selection Mismatch: Expected '{case['selection']}' in '{parsed.selection}'")
                     is_match = False
            
            if is_match and "is_over" in case:
                if parsed.is_over != case["is_over"]:
                    print(f"     Direction Mismatch: Expected Over={case['is_over']}, Got {parsed.is_over}")
                    is_match = False
            
            if is_match:
                print("  [PASS]")
                passed += 1
            else:
                print(f"  [FAIL] Expected {expected_type}, Got {parsed.bet_type.value}")
                
        except Exception as e:
            print(f"  [CRASH] {e}")

    print("="*60)
    print(f"Result: {passed}/{total} ({passed/total*100:.1f}%)")
    print("="*60)

if __name__ == "__main__":
    run_benchmark()
