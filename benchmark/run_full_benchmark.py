import os
import sys
import json
import time
import logging
from typing import List, Dict, Any
from unittest.mock import MagicMock

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.extraction_pipeline import ExtractionPipeline
from src.parallel_batch_processor import parallel_processor
import benchmark.run_autotest as autotest

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Metrics Storage
METRICS = {
    "total_requests": 0,
    "total_tokens_estimated": 0,
    "total_time": 0.0,
    "start_time": 0.0,
    "end_time": 0.0,
}

# Original method
_original_execute = parallel_processor._execute_request


def _patched_execute_request(provider: str, messages: List[dict]) -> str:
    """Patched execution to count metrics."""
    METRICS["total_requests"] += 1

    # Estimate input tokens (approx 4 chars per token)
    prompt_len = sum(len(m.get("content", "")) for m in messages)

    start = time.time()
    try:
        result = _original_execute(provider, messages)
        # Estimate output tokens
        if result:
            response_len = len(result)
            METRICS["total_tokens_estimated"] += (prompt_len + response_len) / 4
        return result
    finally:
        METRICS["total_time"] += time.time() - start


# Apply patch
parallel_processor._execute_request = _patched_execute_request


def load_new_golden_set(path: str) -> Dict:
    """Load and adapt new_golden_set.json to match run_autotest requirements."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    judgments = []
    for item in data:
        # Extract picks as strings
        picks = []
        if "expected_picks" in item:
            for p in item["expected_picks"]:
                if isinstance(p, dict):
                    picks.append(p.get("pick", ""))
                elif isinstance(p, str):
                    picks.append(p)

        judgments.append(
            {
                "message_id": str(item.get("id")),
                "has_picks": len(picks) > 0,
                "picks": picks,
                "capper": item.get("capper", "Unknown"),
            }
        )

    return {"judgments": judgments}


def load_messages_from_ids(ids: List[int], cache_path: str) -> List[Dict]:
    """Load messages corresponding to the golden set IDs."""
    if not os.path.exists(cache_path):
        logging.error(f"Cache file not found: {cache_path}")
        return []

    with open(cache_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle wrapped format
    all_msgs = []
    if isinstance(data, dict) and "messages" in data:
        all_msgs = data["messages"]
    elif isinstance(data, list):
        all_msgs = data
    else:
        # Check for 'unique_msgs.json' format (list of msgs)
        all_msgs = data

    # Create map
    msg_map = {}
    for m in all_msgs:
        if m.get("id"):
            msg_map[str(m["id"])] = m

    # Also load OCR results if available
    ocr_path = os.path.join(os.path.dirname(cache_path), "ocr_results.json")
    if os.path.exists(ocr_path):
        with open(ocr_path, "r", encoding="utf-8") as f:
            ocr_data = json.load(f)
            results = ocr_data.get("results", {})
            for res in results.values():
                mid = str(res.get("msg_id"))
                txt = res.get("text")
                if mid and txt and mid in msg_map:
                    msg_map[mid]["ocr_text"] = txt

    selected = []
    ids_set = set(str(i) for i in ids)
    for mid in ids_set:
        if mid in msg_map:
            selected.append(msg_map[mid])
        else:
            logging.warning(f"Message ID {mid} not found in cache")

    return selected


def main():
    print("=" * 60)
    print("ESTABLISHING BASELINE BENCHMARK")
    print("=" * 60)

    # Paths
    golden_path = os.path.join(BASE_DIR, "benchmark", "clean_golden_set.json")
    if not os.path.exists(golden_path):
        golden_path = os.path.join(BASE_DIR, "new_golden_set.json")

    msgs_path = os.path.join(BASE_DIR, "cache", "messages.json")  # or unique_msgs.json
    # Fallback to unique_msgs.json or data/raw_test_candidates.json
    if not os.path.exists(msgs_path):
        msgs_path = os.path.join(BASE_DIR, "cache", "unique_msgs.json")
    if not os.path.exists(msgs_path):
        msgs_path = os.path.join(BASE_DIR, "data", "raw_test_candidates.json")

    output_path = os.path.join(BASE_DIR, "benchmark", "reports", "baseline_run.json")

    # 1. Load Golden Set & Inputs
    logging.info("Loading Golden Set...")
    try:
        golden_set = load_new_golden_set(golden_path)
    except Exception as e:
        logging.error(f"Failed to load golden set: {e}")
        return

    target_ids = [j["message_id"] for j in golden_set["judgments"]]
    logging.info(f"Targeting {len(target_ids)} messages from Golden Set")

    messages = load_messages_from_ids(target_ids, msgs_path)
    if not messages:
        logging.error("No matching messages found in cache!")
        return

    # 2. Run Pipeline
    logging.info("Starting Pipeline...")
    METRICS["start_time"] = time.time()

    try:
        # Use a dummy date
        picks = ExtractionPipeline.run(messages, target_date="2026-01-24")
    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        import traceback

        traceback.print_exc()
        picks = []

    METRICS["end_time"] = time.time()

    # 3. Save Output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2)
    logging.info(f"Pipeline output saved to {output_path}")

    # 4. Run Accuracy Comparison
    logging.info("Running Accuracy Comparison...")
    comparison_results = autotest.run_comparison(golden_set, picks)

    # 5. Print Full Report
    print("\n" + "=" * 60)
    print("BASELINE PERFORMANCE REPORT")
    print("=" * 60)

    duration = METRICS["end_time"] - METRICS["start_time"]
    avg_latency = METRICS["total_time"] / max(METRICS["total_requests"], 1)

    print(f"PERFORMANCE METRICS:")
    print(f"  Total Duration:     {duration:.2f}s")
    print(f"  Total Requests:     {METRICS['total_requests']}")
    print(f"  Avg Latency (AI):   {avg_latency:.2f}s per request")
    print(f"  Est. Token Usage:   {int(METRICS['total_tokens_estimated'])} tokens")
    print(
        f"  Throughput:         {len(messages) / max(duration, 0.1):.2f} messages/sec"
    )

    print("\nACCURACY METRICS:")
    autotest.print_report(comparison_results)

    # Save combined report
    full_report = {
        "performance": {
            "duration": duration,
            "requests": METRICS["total_requests"],
            "avg_latency": avg_latency,
            "tokens_estimated": METRICS["total_tokens_estimated"],
        },
        "accuracy": comparison_results,
    }

    with open(
        os.path.join(BASE_DIR, "benchmark", "reports", "full_baseline_report.json"), "w"
    ) as f:
        json.dump(full_report, f, indent=2)


if __name__ == "__main__":
    main()
