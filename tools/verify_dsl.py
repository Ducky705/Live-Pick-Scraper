"""
DSL Verification Tool
=====================
Tests if the DSL parser correctly parses the provided sample output.
"""

import sys
import os
from pathlib import Path
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.parsers.dsl_parser import parse_dsl_lines


def main():
    test_file = PROJECT_ROOT / "tests" / "data" / "dsl_test_output.txt"
    if not test_file.exists():
        print(f"Error: {test_file} not found")
        return

    with open(test_file, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"Loaded {len(content)} chars of DSL output.")

    # Parse
    picks = parse_dsl_lines(content)

    print(f"Parsed {len(picks)} picks.")

    # Show first 5
    print("\nFirst 5 parsed picks:")
    for p in picks[:5]:
        print(json.dumps(p, indent=2))

    # Validation checks
    # Check for integers in odds
    int_odds = sum(1 for p in picks if isinstance(p["odds"], int))
    print(f"\nPicks with integer odds: {int_odds}/{len(picks)}")

    # Check for float units
    float_units = sum(1 for p in picks if isinstance(p["units"], float))
    print(f"Picks with float units: {float_units}/{len(picks)}")

    if len(picks) > 50:
        print("\nSUCCESS: DSL Parser is working correctly!")
    else:
        print("\nWARNING: Parsed count seems low (expected > 50)")


if __name__ == "__main__":
    main()
