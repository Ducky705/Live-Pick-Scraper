
from src.grading.validity_filter import ValidityFilter
import logging

# Configure logging to see output
logging.basicConfig(level=logging.INFO)

def test_validity_filter():
    print("Testing ValidityFilter with Team Aliases...")
    
    vf = ValidityFilter()
    
    test_cases = [
        {"text": "(2 u lowa", "expected": True, "note": "Previously Voided"},
        {"text": "Arizona Wildcats", "expected": True, "note": "Previously Voided"},
        {"text": "Clemson", "expected": True, "note": "Previously Voided"},
        {"text": "Santa Clara", "expected": True, "note": "Previously Voided"},
        {"text": "1.5u , Hofstra", "expected": True, "note": "Previously Voided"},
        {"text": "Finland TT Over 3.5", "expected": True, "note": "International Team"},
        {"text": "Analysis below", "expected": False, "note": "Garbage"},
        {"text": "Over 210", "expected": True, "note": "Standard Betting Keyword"},
        {"text": "Lakers -5", "expected": True, "note": "Standard Betting Structure"},
        {"text": "RandomWordThatIsNotATeam", "expected": False, "note": "Should Fail"}
    ]
    
    passes = 0
    for case in test_cases:
        is_valid, reason = vf.is_valid(case["text"])
        result = "PASS" if is_valid == case["expected"] else "FAIL"
        if result == "PASS":
            passes += 1
            
        print(f"[{result}] '{case['text']}': Valid={is_valid} (Reason: {reason})")
        
    print(f"\nTotal Passed: {passes}/{len(test_cases)}")

if __name__ == "__main__":
    test_validity_filter()
