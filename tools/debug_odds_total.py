
import sys
import os
import json
import logging
import re

# Add project root to path
sys.path.insert(0, os.getcwd())

from src.prompts.decoder import normalize_response, ensure_backward_compatible, validate_and_correct_pick, extract_structured_fields

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def test_normalization():
    print("=== TESTING ODDS & TOTALS ===")
    
    # 1. Test Odds Extraction (Negative Sign)
    print("\n--- Test 1: Odds Extraction ---")
    # Case A: Odds in parens
    pick_a = {"t": "ML", "p": "St Bonaventure +7.5 (Odds: -111)", "l": "NCAAB"}
    # Note: validate_and_correct_pick normalizes the pick string first
    validated_a = validate_and_correct_pick(pick_a)
    print(f"Input: {pick_a['p']}")
    print(f"Extracted Odds: {validated_a.get('odds')}")
    
    # Case B: Odds extracted by LLM but passed as int
    pick_b = {"t": "ML", "p": "St Bonaventure +7.5", "o": -111, "l": "NCAAB"}
    validated_b = validate_and_correct_pick(pick_b)
    print(f"Input Odds Field: {pick_b['o']}")
    print(f"Output Odds: {validated_b.get('odds')}")
    
    # 2. Test Total Formatting
    print("\n--- Test 2: Total Formatting ---")
    pick_total = {"t": "TL", "p": "St Louis/St Bonnies Under 158.5", "l": "NCAAB"}
    validated_total = validate_and_correct_pick(pick_total)
    print(f"Input: {pick_total['p']}")
    print(f"Output Pick: {validated_total.get('pick')}")
    
    if " vs " in validated_total.get('pick', ''):
        print("PASS: 'vs' separator used")
    else:
        print("FAIL: 'vs' separator NOT used")

if __name__ == "__main__":
    test_normalization()
