import json
import logging
import os
import statistics
import sys
import time
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from benchmark.run_autotest import run_comparison
from src.extraction_pipeline import ExtractionPipeline

# Configure logging
logging.basicConfig(level=logging.ERROR)  # Suppress noise, we want clean output
logger = logging.getLogger("Benchmark")
logger.setLevel(logging.INFO)

# Metrics Store
METRICS = {"requests": 0, "tokens_in": 0, "tokens_out": 0, "latencies": []}

# Wrapper to intercept provider calls
# We patch ParallelBatchProcessor._execute_request because that's what the pipeline uses
from src.parallel_batch_processor import ParallelBatchProcessor

original_execute_request = ParallelBatchProcessor._execute_request


def tracked_execute_request(self, provider, messages):
    start = time.time()
    METRICS["requests"] += 1

    # Estimate tokens
    # Messages is a list of dicts, so we stringify it for rough count
    if messages:
        METRICS["tokens_in"] += len(str(messages)) / 4

    try:
        # Execute actual call
        result = original_execute_request(self, provider, messages)

        duration = time.time() - start
        METRICS["latencies"].append(duration)

        if result:
            METRICS["tokens_out"] += len(str(result)) / 4

        return result
    except Exception as e:
        # Track latency even for errors
        duration = time.time() - start
        METRICS["latencies"].append(duration)
        raise e


def main():
    print("=" * 60)
    print("PERFORMANCE BENCHMARK - BASELINE ESTABLISHMENT")
    print("=" * 60)

    # 1. Load Input Messages from Golden Set (for consistent benchmarking)
    input_path = os.path.abspath("new_golden_set.json")
    if not os.path.exists(input_path):
        print(f"ERROR: {input_path} not found.")
        return

    with open(input_path, encoding="utf-8") as f:
        golden_data = json.load(f)

    messages = []
    for item in golden_data:
        # Map golden set item to TelegramMessage dict structure
        msg = {
            "id": item.get("id"),
            "text": item.get("text", ""),
            "date": item.get("date", "2026-01-01 12:00 ET"),
            "images": item.get("images", []),
            "channel_id": item.get("channel_id", 0),
            "channel_name": item.get("channel_name", "BenchmarkChannel"),
            "ocr_text": "",
            "ocr_texts": [],
        }
        messages.append(msg)

    print(f"Loaded {len(messages)} messages from Golden Set for benchmarking.")

    # 2. Run Pipeline with Instrumentation
    print("\n[Running Extraction Pipeline...]")
    start_total = time.time()

    # Patch the class method
    with patch(
        "src.parallel_batch_processor.ParallelBatchProcessor._execute_request",
        side_effect=tracked_execute_request,
        autospec=True,
    ):
        # target_date is arbitrary for benchmarking parsing logic
        picks = ExtractionPipeline.run(messages, target_date="2026-01-27")

    elapsed_total = time.time() - start_total
    print(f"Pipeline completed in {elapsed_total:.2f}s")

    # 3. Save Output (for debugging)
    output_path = os.path.join("benchmark", "reports", "benchmark_picks.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2)

    # 4. Calculate Accuracy
    # golden_path = os.path.join("benchmark", "reports", "auto_golden_set.json")
    golden_path = os.path.abspath("new_golden_set.json")
    if not os.path.exists(golden_path):
        print(f"\n[WARNING] Golden set not found at {golden_path}. Skipping accuracy check.")
        accuracy = 0.0
        accuracy_report = {}
    else:
        print(f"\n[Verifying Accuracy against Golden Set: {golden_path}]")
        with open(golden_path, encoding="utf-8") as f:
            golden_set = json.load(f)

        # Helper to format for run_comparison
        if isinstance(golden_set, list):
            # Map 'expected_picks' to 'picks' and 'has_picks' if needed
            for j in golden_set:
                if "expected_picks" in j and "picks" not in j:
                    j["picks"] = [p["pick"] for p in j["expected_picks"]]
                    j["has_picks"] = len(j["picks"]) > 0
                    j["message_id"] = j.get("id")
            golden_wrapper = {"judgments": golden_set}
        else:
            golden_wrapper = golden_set

        accuracy_report = run_comparison(golden_wrapper, picks)
        accuracy = accuracy_report.get("metrics", {}).get("accuracy", 0.0)

    # 5. Final Report
    avg_latency = statistics.mean(METRICS["latencies"]) if METRICS["latencies"] else 0
    total_tokens = int(METRICS["tokens_in"] + METRICS["tokens_out"])

    print("\n" + "=" * 60)
    print("FINAL BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Total Requests Sent: {METRICS['requests']}")
    print(f"Avg Latency (API):   {avg_latency:.2f}s")
    print(f"Token Usage (Est):   {total_tokens} tokens")
    print(f"Accuracy:            {accuracy}%")
    print("=" * 60)

    # Dump metrics to file for comparison later
    metrics_file = os.path.join("benchmark", "reports", "last_run_metrics.json")
    with open(metrics_file, "w") as f:
        json.dump(
            {
                "requests": METRICS["requests"],
                "avg_latency": avg_latency,
                "tokens": total_tokens,
                "accuracy": accuracy,
            },
            f,
            indent=2,
        )


if __name__ == "__main__":
    main()
