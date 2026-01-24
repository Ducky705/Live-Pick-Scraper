
import sys
import os
import json
import logging

# Add project root to path
sys.path.insert(0, os.getcwd())

from src.prompts.decoder import normalize_response, ensure_backward_compatible, validate_and_correct_pick

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def test_normalization():
    print("=== TESTING NORMALIZATION ===")
    
    # 1. Test ensure_backward_compatible directly
    print("\n--- Test 1: ensure_backward_compatible ---")
    compact_pick = {"t": "SP", "p": "Lakers -5", "l": "NBA"}
    expanded = ensure_backward_compatible(compact_pick)
    print(f"Input: {compact_pick}")
    print(f"Output: {expanded}")
    
    if expanded.get('type') != "Spread":
        print("FAIL: 't': 'SP' did not expand to 'type': 'Spread'")
    else:
        print("PASS: Type expansion worked in ensure_backward_compatible")

    # 2. Test validate_and_correct_pick
    print("\n--- Test 2: validate_and_correct_pick ---")
    # This function calls ensure_backward_compatible internally
    validated = validate_and_correct_pick(compact_pick)
    print(f"Validated: {json.dumps(validated, indent=2)}")
    
    if validated.get('type') != "Spread":
        print(f"FAIL: Final type is {validated.get('type')}, expected 'Spread'")
    
    # Check structured fields
    if validated.get('line') != -5.0:
        print(f"FAIL: Line not extracted! Got {validated.get('line')}")
    else:
        print("PASS: Line extracted correctly")

if __name__ == "__main__":
    test_normalization()
