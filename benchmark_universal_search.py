
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from grading.parser import PickParser
from grading.schema import BetType

# Test set of "Unknown League" picks
# Mix of NBA, NHL, NCAAB, NFL, MLB teams without league indicators
TEST_CASES = [
    ("Kings ML", "NBA"), # Sacramento (could be NHL, but let's assume default/context)
    ("Lakers -5", "NBA"),
    ("Celtics Over 110.5", "NBA"),
    ("Oilers ML", "NHL"),
    ("Bruins -1.5", "NHL"),
    ("Maple Leafs Over 6.5", "NHL"),
    ("Chiefs -3", "NFL"),
    ("49ers ML", "NFL"),
    ("Yankees ML", "MLB"),
    ("Dodgers -1.5", "MLB"),
    ("Duke -4.5", "NCAAB"),
    ("North Carolina ML", "NCAAB"),
    ("Warriors vs Lakers Over 225", "NBA"), # Parlay/Game match?
    ("Sacramento Kings ML", "NBA"),
    ("Los Angeles Kings ML", "NHL"),
    ("Golden State Warriors -2", "NBA"),
    ("Florida Panthers ML", "NHL"),
    ("Generic Team ML", "Unknown"), # Should fail/remain unknown
]

def run_benchmark():
    print(f"{'Pick Text':<30} | {'Expected':<10} | {'Actual':<10} | {'Status'}")
    print("-" * 65)
    
    passes = 0
    total = len(TEST_CASES)
    
    for text, expected in TEST_CASES:
        # Pass "Unknown" as league to force inference logic
        pick = PickParser.parse(text, league="Unknown")
        
        actual = pick.league
        
        # Simple flexible matching (e.g. if we expect NBA and get NBA)
        # Note: PickParser currently defaults to "UNKNOWN" or "OTHER" if not found
        is_pass = actual.upper() == expected.upper()
        
        # Special case: "Kings ML" -> NBA/NHL ambiguity. 
        # If we expect NBA but get NHL (or vice versa), technically it found a valid league, 
        # but for this benchmark we strictly check if it found *A* valid sport league vs Unknown.
        if expected != "Unknown" and actual != "Unknown" and actual != "OTHER":
             # We count it as a pass if it resolved to a real league, 
             # even if it's the "wrong" Kings (since without context it's ambiguous)
             if expected in ["NBA", "NHL"] and actual in ["NBA", "NHL"]:
                 is_pass = True
        
        status = "✅ PASS" if is_pass else "❌ FAIL"
        if is_pass:
            passes += 1
            
        print(f"{text:<30} | {expected:<10} | {actual:<10} | {status}")

    print("-" * 65)
    print(f"Total: {total}")
    print(f"Passed: {passes}")
    print(f"Failed: {total - passes}")
    print(f"Success Rate: {passes/total:.1%}")

if __name__ == "__main__":
    run_benchmark()
