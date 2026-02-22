import json
import logging
import os
import sys
import time

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import benchmark.run_autotest as autotest
from src.extraction_pipeline import ExtractionPipeline
from src.parallel_batch_processor import parallel_processor

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Metrics Storage
METRICS = {
    "total_requests": 0,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_time": 0.0,
    "start_time": 0.0,
    "end_time": 0.0,
}

# --- Patching for Efficiency Tracking ---
_original_execute = parallel_processor._execute_request


def _patched_execute_request(provider: str, messages: list[dict], **kwargs) -> str:
    """Patched execution to count metrics."""
    METRICS["total_requests"] += 1

    # Estimate input tokens (approx 4 chars per token)
    prompt_len = sum(len(m.get("content", "")) for m in messages)
    METRICS["total_input_tokens"] += prompt_len / 4

    start = time.time()
    try:
        result = _original_execute(provider, messages, **kwargs)
        # Estimate output tokens
        if result:
            response_len = len(result)
            METRICS["total_output_tokens"] += response_len / 4
        return result
    finally:
        METRICS["total_time"] += time.time() - start


# Apply patch
parallel_processor._execute_request = _patched_execute_request


def load_goldenset(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_grader():
    goldenset_path = os.path.join(BASE_DIR, "benchmark", "dataset", "goldenset_platform_500.json")
    if not os.path.exists(goldenset_path):
        print(f"Error: Goldenset not found at {goldenset_path}")
        return

    print("=" * 60)
    print("PLATFORM GRADER: ACCURACY, SPEED, EFFICIENCY")
    print("=" * 60)

    # 1. Load Data
    goldenset = load_goldenset(goldenset_path)

    # Check for FULL_BENCHMARK env var
    if os.environ.get("FULL_BENCHMARK") == "1":
        print("RUNNING FULL BENCHMARK (500 items)")
    else:
        # CRITICAL: Limit to 50 for rapid debugging cycle
        print("RUNNING PARTIAL BENCHMARK (50 items) - Set FULL_BENCHMARK=1 for full run")
        goldenset = goldenset[:50]

    print(f"Loaded {len(goldenset)} messages from goldenset.")

    # Convert goldenset to input format for pipeline
    input_messages = []
    for item in goldenset:
        input_messages.append(
            {
                "id": item["message_id"],
                "text": item["text"],
                "source": item.get("source", "unknown"),
                "author": item.get("capper", "Unknown"),  # US-004: Pass capper to prevent global dedup issues
                "date": "2026-01-24 12:00 ET",  # Mock date
            }
        )

    # 2. Run Pipeline
    logging.info("Starting Extraction Pipeline...")
    METRICS["start_time"] = time.time()

    try:
        # Run pipeline (using parallel processor internally)
        scraped_picks = ExtractionPipeline.run(input_messages, target_date="2026-01-24")
    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        import traceback

        traceback.print_exc()
        scraped_picks = []

    METRICS["end_time"] = time.time()
    duration = METRICS["end_time"] - METRICS["start_time"]

    # 3. Grade Accuracy
    # Prepare goldenset for autotest (needs specific structure)
    # autotest expects list of judgments
    judgments = []
    for item in goldenset:
        judgments.append(
            {
                "message_id": item["message_id"],
                "has_picks": True,
                "picks": item["expected_picks"],
                "capper": item.get("capper"),
            }
        )

    wrapped_goldenset = {"judgments": judgments}

    print("\nRunning Accuracy Analysis...")
    accuracy_results = autotest.run_comparison(wrapped_goldenset, scraped_picks)

    # PRINT DETAILED REPORT
    autotest.print_report(accuracy_results)

    # Check for --save-failures flag
    if "--save-failures" in sys.argv:
        failures_path = os.path.join(BASE_DIR, "benchmark", "reports", "failures.json")
        with open(failures_path, "w", encoding="utf-8") as f:
            json.dump(accuracy_results, f, indent=2)
        print(f"\nFailures saved to {failures_path}")

    # 4. Generate Report
    print("\n" + "=" * 60)
    print("FINAL GRADING REPORT")
    print("=" * 60)

    # Speed Metrics
    throughput = len(input_messages) / max(duration, 0.1)
    latency_per_msg = duration / max(len(input_messages), 1)

    print("\nSPEED:")
    print(f"  Total Duration:     {duration:.2f}s")
    print(f"  Throughput:         {throughput:.2f} msgs/sec")
    print(f"  Avg Latency:        {latency_per_msg * 1000:.2f} ms/msg")

    # Efficiency Metrics
    total_tokens = METRICS["total_input_tokens"] + METRICS["total_output_tokens"]
    tokens_per_pick = total_tokens / max(accuracy_results["metrics"]["total_picks_found"], 1)
    requests_per_msg = METRICS["total_requests"] / max(len(input_messages), 1)

    print("\nEFFICIENCY:")
    print(f"  Total AI Prompts:   {METRICS['total_requests']}")
    print(f"  Prompts/Message:    {requests_per_msg:.2f}")
    print(f"  Est. Total Tokens:  {int(total_tokens)}")
    print(f"  Tokens/Pick Found:  {int(tokens_per_pick)}")

    # Accuracy Metrics
    acc = accuracy_results["metrics"]
    print("\nACCURACY:")
    print(f"  Precision:          {acc['precision']}%")
    print(f"  Recall:             {acc['recall']}%")
    print(
        f"  F1 Score:           {2 * (acc['precision'] * acc['recall']) / max(acc['precision'] + acc['recall'], 0.01):.2f}%"
    )
    print(f"  Total Picks Found:  {acc['total_picks_found']}")
    print(f"  False Positives:    {acc['total_false_positives']}")
    print(f"  Missed Picks:       {acc['total_missed']}")

    # Save Results
    report = {
        "speed": {"duration": duration, "throughput": throughput, "latency_ms": latency_per_msg * 1000},
        "efficiency": {
            "total_requests": METRICS["total_requests"],
            "requests_per_msg": requests_per_msg,
            "total_tokens": total_tokens,
        },
        "accuracy": acc,
    }

    with open(os.path.join(BASE_DIR, "benchmark", "reports", "final_platform_grade.json"), "w") as f:
        json.dump(report, f, indent=2)

    print("\nDetailed report saved to benchmark/reports/final_platform_grade.json")


if __name__ == "__main__":
    run_grader()
