import json
import logging
import os
import sys
import time

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.extraction_pipeline import ExtractionPipeline
from src.parallel_batch_processor import parallel_processor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Benchmark")


def normalize_string(s):
    if not s:
        return ""
    s = str(s).lower()
    s = s.replace("/", " ").replace("-", " ").replace(":", " ").replace("|", " ")
    s = s.replace("'", "").replace('"', "").replace("“", "").replace("”", "").replace("(", "").replace(")", "")
    s = s.replace(" vs ", " ").replace(" versus ", " ").replace(" @ ", " ").replace(" games", "")
    s = s.replace("dnb", "draw no bet")
    s = s.replace("ah", "asian handicap")
    return s.strip()


def fuzzy_match(expected, actual):
    # Core fields to check
    # 1. Pick (Most important)
    exp_pick_raw = normalize_string(expected.get("pick"))
    act_pick_raw = normalize_string(actual.get("pick"))

    # Tokenize
    exp_tokens = set(exp_pick_raw.split())
    act_tokens = set(act_pick_raw.split())

    # Remove common filler words
    stop_words = {"the", "a", "an", "bet", "pick", "prediction", "of", "in", "ml", "moneyline"}
    exp_tokens -= stop_words
    act_tokens -= stop_words

    # Check for name overlap (Crucial)
    intersection = exp_tokens.intersection(act_tokens)

    # Calculate overlap ratio relative to expected length
    if not exp_tokens:
        return False
    ratio = len(intersection) / len(exp_tokens)

    pick_match = (ratio >= 0.5) or (exp_pick_raw in act_pick_raw) or (act_pick_raw in exp_pick_raw)

    # 3. Odds
    odds_match = True
    if expected.get("odds") and actual.get("odds"):
        try:
            exp_odd = float(expected.get("odds"))
            act_odd = float(actual.get("odds"))
            if abs(exp_odd) > 5.0:  # Likely American
                odds_match = abs(exp_odd - act_odd) <= 10.0  # Allow -110 vs -115 difference
            else:
                odds_match = abs(exp_odd - act_odd) <= 0.05
        except:
            pass

    return pick_match and odds_match


def run_benchmark():
    print("Loading Golden Set v2...")
    try:
        with open("new_golden_set_v2.json", encoding="utf-8") as f:
            golden_set = json.load(f)
    except FileNotFoundError:
        print("Error: new_golden_set_v2.json not found.")
        return

    # Convert to pipeline messages
    messages = []
    golden_map = {}
    for item in golden_set:
        msg_id = str(item["id"])
        msg = {
            "id": msg_id,
            "date": item["date"],
            "text": item["text"],
            "images": item.get("images", []),
            "ocr_text": "",
            "ocr_texts": [],
            "source": item.get("source", "Telegram"),
        }
        messages.append(msg)
        golden_map[msg_id] = item.get("expected_picks", [])

    print(f"Loaded {len(messages)} test cases.")

    # Reset Processor Stats
    for p in parallel_processor.stats:
        parallel_processor.stats[p] = {"count": 0, "errors": 0, "total_time": 0.0}

    # Run Pipeline (Standard System Benchmark)
    print("Running Benchmark...")
    start_time = time.time()

    # Pass target_date=None to ensure all messages are processed regardless of date
    try:
        actual_picks = ExtractionPipeline.run(messages, target_date="2026-02-02")
    except Exception as e:
        print(f"CRITICAL ERROR: Pipeline failed. {e}")
        import traceback

        traceback.print_exc()
        return

    end_time = time.time()
    total_duration = end_time - start_time

    # Collect Stats
    total_calls = sum(s["count"] for s in parallel_processor.stats.values())

    # Calculate Accuracy
    total_expected = 0
    total_correct = 0

    actual_map = {}
    for p in actual_picks:
        mid = str(p.get("message_id"))
        if mid not in actual_map:
            actual_map[mid] = []
        actual_map[mid].append(p)

    print("\nBENCHMARK RESULTS")
    print("-" * 30)

    for mid, expected_list in golden_map.items():
        actual_list = actual_map.get(mid, [])
        total_expected += len(expected_list)

        matched_indices = set()
        for exp in expected_list:
            found = False
            for i, act in enumerate(actual_list):
                if i in matched_indices:
                    continue
                if fuzzy_match(exp, act):
                    found = True
                    matched_indices.add(i)
                    total_correct += 1
                    break

    accuracy = (total_correct / total_expected * 100) if total_expected > 0 else 0

    print(f"Total Time:      {total_duration:.2f}s")
    print(f"Total AI Calls:  {total_calls}")
    print(f"Total Items:     {len(messages)}")
    print(f"Expected Picks:  {total_expected}")
    print(f"Correct Picks:   {total_correct}")
    print(f"Accuracy Score:  {accuracy:.2f}%")

    print("-" * 30)
    print("Calls per Provider:")
    for p, s in parallel_processor.stats.items():
        if s["count"] > 0:
            print(f"  - {p}: {s['count']}")


if __name__ == "__main__":
    run_benchmark()
