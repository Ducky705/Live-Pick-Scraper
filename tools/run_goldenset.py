
import json
import logging
import sys
import os
from dotenv import load_dotenv
from dataclasses import asdict

load_dotenv()

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.grading.engine import GraderEngine
from src.grading.schema import GradeResult

# Setup logging
logging.basicConfig(level=logging.WARNING)

GOLDENSET_PATH = "tests/goldenset.json"
FIXTURES_PATH = "tests/fixtures/goldenset_scores.json"

def run_benchmark():
    print(f"--- Running Goldenset Benchmark ---")
    
    # 1. Load Fixtures
    if not os.path.exists(FIXTURES_PATH):
        print(f"❌ Fixtures not found at {FIXTURES_PATH}")
        return
        
    with open(FIXTURES_PATH, "r") as f:
        scores = json.load(f)
    print(f"Loaded {len(scores)} fixture games.")
    
    # 2. Load Tests
    if not os.path.exists(GOLDENSET_PATH):
        print(f"❌ Goldenset tests not found at {GOLDENSET_PATH}")
        return

    with open(GOLDENSET_PATH, "r") as f:
        tests = json.load(f)
    print(f"Loaded {len(tests)} test cases.")
    
    # 3. Initialize Engine with Mock Data
    # Engine takes a list of dicts, which is exactly what scores is
    engine = GraderEngine(scores)
    
    # 4. Run Tests
    passed = 0
    failed = 0
    
    print("\n--- Execution ---")
    
    for test in tests:
        # Construct a pick object (simple dict for batch processing)
        pick_input = {
            "pick": test["pick"],
            "league": test["league"]
        }
        
        # Grade 
        # Note: grade_batch expects a list of dicts with 'pick' and 'league'
        results = engine.grade_batch([pick_input])
        result = results[0]
        
        expected_grade = test["expected"]
        actual_grade = result.grade.value
        
        # Check Assertions
        if expected_grade == "RESOLVED":
            # Pass if outcome is definitive (WIN, LOSS, PUSH, VOID)
            # Fail if PENDING or ERROR
            is_pass = actual_grade in ["WIN", "LOSS", "PUSH", "VOID"]
        else:
            is_pass = (actual_grade == expected_grade)
        
        status_icon = "✅" if is_pass else "❌"
        print(f"{status_icon} [{test['desc']}]")
        print(f"   Pick: {test['pick']}")
        print(f"   Expected: {expected_grade} | Actual: {actual_grade} | League: {result.pick.league}")
        
        if not is_pass:
            print(f"   ⚠️ FAILURE DETAILS: {result.details or result.score_summary}")
            print(f"   Matched Game ID: {result.game_id}")
            failed += 1
        else:
            passed += 1
            
    print("\n--- Summary ---")
    print(f"Total: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🏆 GOLDENSET PASSED 🏆")
        sys.exit(0)
    else:
        print("\n💥 GOLDENSET FAILED 💥")
        sys.exit(1)

if __name__ == "__main__":
    run_benchmark()
