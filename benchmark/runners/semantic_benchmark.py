"""
Semantic Validator Benchmark
============================
Tests the logic engine against known edge cases.
"""

import json
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.semantic_validator import SemanticValidator


def run_semantic_benchmark():
    dataset_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dataset", "semantic_test_cases.json")

    if not os.path.exists(dataset_path):
        print(f"Dataset not found: {dataset_path}")
        return

    with open(dataset_path) as f:
        test_cases = json.load(f)

    print(f"Running Semantic Benchmark on {len(test_cases)} cases...\n")

    passed = 0
    failed = 0

    for case in test_cases:
        pick = case["input_pick"]
        expected_valid = case["expected_valid"]
        case_id = case.get("id", "Unknown")

        # Run Validator
        is_valid, reason = SemanticValidator.validate(pick)

        # Check Result
        if is_valid == expected_valid:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"

        print(f"[{status}] {case_id}: Expected {expected_valid}, Got {is_valid}")
        if not is_valid:
            print(f"   Reason: {reason}")
        if status == "FAIL":
            print(f"   Input: {pick}")
        print("-" * 40)

    print(f"\nResults: {passed}/{len(test_cases)} Passed ({passed / len(test_cases):.0%})")


if __name__ == "__main__":
    run_semantic_benchmark()
