import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.grading.validity_filter import ValidityFilter

test_cases = [
    ("Over 6.5", "Unknown", False),  # Invalid numeric
    ("Team ML", "Unknown", False),   # Invalid generic
    ("-7.5", "Unknown", False),       # Invalid numeric
    ("Lakers -5", "NBA", True),       # Valid
    ("LeBron O 25.5", "NBA", True),   # Valid
    ("If 1P ends 0:0 I'm taking Over 4.5 full game", "Soccer", False), # Conditional/Complex/Chatty
    ("Check out my VIP", "Unknown", False), # Spam
]

val = ValidityFilter()

print("Running Validity Tests...")
for text, league, expected in test_cases:
    is_valid, reason = val.is_valid(text, league)
    status = "PASS" if is_valid == expected else "FAIL"
    print(f"[{status}] '{text}' -> {is_valid} (Reason: {reason})")
