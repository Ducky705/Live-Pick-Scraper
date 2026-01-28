import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

import time
import logging
from unittest.mock import MagicMock, patch
from src.parallel_batch_processor import (
    ParallelBatchProcessor,
    AdaptiveConcurrencyLimiter,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_adaptive_concurrency():
    print("\n=== STARTING US-001 VERIFICATION: Adaptive Concurrency Control ===")

    # Initialize processor
    processor = ParallelBatchProcessor()
    limiter = processor.adaptive_limiter

    # 1. Verify Initial State
    print(f"\n[Check 1] Initial State")
    print(f"Initial Limit: {limiter.limit} (Expected: 4)")
    assert limiter.limit == 4, f"Expected initial limit 4, got {limiter.limit}"

    # 2. Verify Backoff on 429
    print(f"\n[Check 2] Backoff Logic")
    # Simulate 429
    limiter.record_429()
    print(f"Limit after 1st 429: {limiter.limit} (Expected: 2)")
    assert limiter.limit == 2, f"Expected limit 2, got {limiter.limit}"

    limiter.record_429()
    print(f"Limit after 2nd 429: {limiter.limit} (Expected: 1)")
    assert limiter.limit == 1, f"Expected limit 1, got {limiter.limit}"

    # Verify min limit
    limiter.record_429()
    print(f"Limit after 3rd 429: {limiter.limit} (Expected: 1 - Min Limit)")
    assert limiter.limit == 1, f"Expected limit 1, got {limiter.limit}"

    # 3. Verify Recovery (10 successful requests)
    print(f"\n[Check 3] Recovery Logic")

    # Simulate 9 successes
    for i in range(9):
        limiter.record_success()

    print(f"Limit after 9 successes: {limiter.limit} (Expected: 1)")
    assert limiter.limit == 1, "Limit should not increase yet"

    # 10th success
    limiter.record_success()
    print(f"Limit after 10 successes: {limiter.limit} (Expected: 2)")
    assert limiter.limit == 2, f"Expected limit 2, got {limiter.limit}"

    # Simulate another 10 successes
    for i in range(10):
        limiter.record_success()

    print(f"Limit after another 10 successes: {limiter.limit} (Expected: 3)")
    assert limiter.limit == 3, f"Expected limit 3, got {limiter.limit}"

    print("\n=== US-001 VERIFICATION PASSED ===")


def test_integration():
    print("\n=== STARTING INTEGRATION TEST ===")

    # Mock the execute_request to simulate 429s
    processor = ParallelBatchProcessor()

    # Reset limiter to known state
    processor.adaptive_limiter.limit = 4
    processor.adaptive_limiter.success_streak = 0

    # Mock _execute_request
    original_execute = processor._execute_request

    call_count = 0

    def mock_execute(provider, messages):
        nonlocal call_count
        call_count += 1
        # Succeed first 2 times
        if call_count <= 2:
            return "Success"
        # Fail next 2 times with 429
        elif call_count <= 4:
            raise Exception("429 Too Many Requests")
        # Succeed afterwards
        else:
            return "Success"

    processor._execute_request = mock_execute

    # Create dummy batches
    batches = [[{"role": "user", "content": "test"}] for _ in range(10)]

    # Run processor (this uses threads, so we can't easily assert inside strict order,
    # but we can check the final state of the limiter)

    # We expect 2 429s.
    # Initial: 4
    # 1st 429: limit -> 2
    # 2nd 429: limit -> 1
    # Then successes...

    # Note: Because of threading, the exact order of execution isn't guaranteed deterministic
    # regarding WHEN the 429s hit relative to other starts, but eventually it should drop.

    print("Running process_batches with simulated 429s...")
    results = processor.process_batches(batches)

    print(f"Final Limit: {processor.adaptive_limiter.limit}")
    print(f"Total Batches Processed: {len(results)}")

    # Verification
    # We tried to force at least 2 errors.
    # The limiter should have dropped to at least 2.
    if processor.adaptive_limiter.limit < 4:
        print("Integration Test Passed: Limit dropped below initial value.")
    else:
        print("Integration Test Failed: Limit did not drop.")
        raise AssertionError("Limit did not drop on 429s")


if __name__ == "__main__":
    try:
        test_adaptive_concurrency()
        test_integration()
    except AssertionError as e:
        print(f"\nVERIFICATION FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        exit(1)
