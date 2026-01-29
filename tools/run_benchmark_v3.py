#!/usr/bin/env python3
"""
Run Benchmark V3
================
Runs the local pipeline against the saved Goldenset Truth.
Calculates Precision, Recall, F1, and Field-Level Accuracy.
"""

import asyncio
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()

# --- IMPORT PIPELINE COMPONENTS ---
from src.parallel_batch_processor import parallel_processor
from src.prompts.decoder import normalize_response
from src.utils import backfill_odds

# --- CONFIG ---
DATA_DIR = PROJECT_ROOT / "tests" / "data"
INPUT_FILE = DATA_DIR / "goldenset_inputs.json"
TRUTH_FILE = DATA_DIR / "goldenset_truth.json"
REPORT_FILE = DATA_DIR / "benchmark_report.md"


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def normalize_pick_string(s):
    """Normalize pick string for comparison (ignore case, spaces)"""
    if not s:
        return ""
    return str(s).lower().replace(" ", "").strip()


def to_int(val):
    try:
        return int(val)
    except:
        return -1


def compare_picks(local_picks, truth_picks):
    """
    Compare local picks against truth using fuzzy matching.
    Returns (tp, fp, fn, detailed_stats)
    """
    import difflib

    tp = 0
    fp = 0
    fn = 0

    # Map truth by message_id (ensure int)
    truth_map = defaultdict(list)
    for p in truth_picks:
        truth_map[to_int(p["message_id"])].append(p)

    # Map local by message_id (ensure int)
    local_map = defaultdict(list)
    for p in local_picks:
        local_map[to_int(p["message_id"])].append(p)

    detailed_stats = {
        "league_matches": 0,
        "type_matches": 0,
        "odds_matches": 0,
        "units_matches": 0,
        "total_matched_picks": 0,
    }

    matches = []  # List of (truth, local) pairs

    all_msg_ids = set(truth_map.keys()) | set(local_map.keys())

    for mid in all_msg_ids:
        t_list = truth_map.get(mid, [])
        l_list = local_map.get(mid, [])

        matched_indices = set()

        for t_pick in t_list:
            best_match = None
            best_idx = -1
            best_score = 0.0

            t_norm = normalize_pick_string(t_pick["pick"])

            for idx, l_pick in enumerate(l_list):
                if idx in matched_indices:
                    continue

                l_norm = normalize_pick_string(l_pick["pick"])

                # Exact Normalized Match
                if t_norm == l_norm:
                    best_match = l_pick
                    best_idx = idx
                    best_score = 1.0
                    break

                # Substring Match (high confidence)
                if t_norm in l_norm or l_norm in t_norm:
                    best_match = l_pick
                    best_idx = idx
                    best_score = 0.95
                    break

                # Fuzzy Match (SequenceMatcher)
                ratio = difflib.SequenceMatcher(None, t_norm, l_norm).ratio()
                if ratio > 0.7 and ratio > best_score:  # Threshold 0.7
                    best_match = l_pick
                    best_idx = idx
                    best_score = ratio

            if best_match:
                tp += 1
                matched_indices.add(best_idx)
                matches.append((t_pick, best_match))

                # Check fields
                if str(t_pick.get("league")).lower() == str(best_match.get("league")).lower():
                    detailed_stats["league_matches"] += 1

                if str(t_pick.get("type")).lower() == str(best_match.get("type")).lower():
                    detailed_stats["type_matches"] += 1

                # Odds (allow slight variation or None)
                t_odds = t_pick.get("odds")
                l_odds = best_match.get("odds")
                if t_odds == l_odds:
                    detailed_stats["odds_matches"] += 1
                elif t_odds and l_odds and abs(int(t_odds) - int(l_odds)) <= 5:  # Tolerance
                    detailed_stats["odds_matches"] += 1

                # Units
                t_units = float(t_pick.get("units") or 1.0)
                l_units = float(best_match.get("units") or 1.0)
                if abs(t_units - l_units) < 0.1:
                    detailed_stats["units_matches"] += 1

                detailed_stats["total_matched_picks"] += 1

            else:
                fn += 1  # Missed this truth pick

    # Remaining local picks are False Positives
    # fp += len(l_list) - len(matched_indices)
    # Logic fix: We iterate over message IDs, so we need to calc FP per message
    # Re-loop to calc FP correctly

    total_local_picks = sum(len(local_map[mid]) for mid in all_msg_ids)
    fp = total_local_picks - tp

    debug_log = []

    for mid in sorted(list(all_msg_ids))[:5]:
        t_list = truth_map.get(mid, [])
        l_list = local_map.get(mid, [])

        debug_log.append(f"\n--- MSG {mid} ---")
        debug_log.append("TRUTH:")
        for t in t_list:
            debug_log.append(f"  ID: {t.get('message_id')} | Pick: {t.get('pick')}")
        debug_log.append("LOCAL:")
        for l in l_list:
            debug_log.append(f"  ID: {l.get('message_id')} | Pick: {l.get('pick')}")

    with open(DATA_DIR / "benchmark_debug.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(debug_log))
    print(f"Debug log saved to {DATA_DIR / 'benchmark_debug.txt'}")

    return tp, fp, fn, detailed_stats


async def run_pipeline(messages):
    """Run the actual extraction pipeline on messages"""
    print(f"Running pipeline on {len(messages)} messages...")

    # 1. OCR is already done in the input file (ocr_text field)
    # 2. Parallel Processing
    batches = [messages[i : i + 10] for i in range(0, len(messages), 10)]

    raw_responses = parallel_processor.process_batches(batches)

    local_picks = []

    for batch_idx, raw in enumerate(raw_responses):
        if batch_idx < len(batches):
            current_batch = batches[batch_idx]
            valid_ids = [m["id"] for m in current_batch]

            # Expand = True handles the compact format
            picks = normalize_response(raw, expand=True, valid_message_ids=valid_ids)
            local_picks.extend(picks)

    local_picks = backfill_odds(local_picks)
    return local_picks


def generate_report(tp, fp, fn, stats, duration):
    """Generate Markdown report"""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    total = stats["total_matched_picks"]
    acc_league = stats["league_matches"] / total if total > 0 else 0
    acc_type = stats["type_matches"] / total if total > 0 else 0
    acc_odds = stats["odds_matches"] / total if total > 0 else 0
    acc_units = stats["units_matches"] / total if total > 0 else 0

    report = f"""# Benchmark Report (V3)

**Date:** {time.strftime("%Y-%m-%d %H:%M:%S")}
**Duration:** {duration:.2f}s

## 🎯 Overall Performance

| Metric | Score |
| :--- | :--- |
| **F1 Score** | **{f1:.2%}** |
| Precision | {precision:.2%} |
| Recall | {recall:.2%} |

## 📊 Extraction Stats
- **True Positives (Correct):** {tp}
- **False Positives (Hallucinations):** {fp}
- **False Negatives (Missed):** {fn}

## 🔍 Field Accuracy (on matched picks)
| Field | Accuracy | Matches |
| :--- | :--- | :--- |
| **League** | {acc_league:.1%} | {stats["league_matches"]}/{total} |
| **Bet Type** | {acc_type:.1%} | {stats["type_matches"]}/{total} |
| **Odds** | {acc_odds:.1%} | {stats["odds_matches"]}/{total} |
| **Units** | {acc_units:.1%} | {stats["units_matches"]}/{total} |

"""
    return report


def main():
    print(f"{Colors.BOLD}Starting Benchmark V3...{Colors.RESET}")

    # 1. Load Data
    if not INPUT_FILE.exists() or not TRUTH_FILE.exists():
        print(f"{Colors.RED}Error: Data files not found in {DATA_DIR}{Colors.RESET}")
        return

    inputs = load_json(INPUT_FILE)
    truth_data = load_json(TRUTH_FILE)
    truth_picks = truth_data.get("picks", [])

    print(f"Loaded {len(inputs)} input messages.")
    print(f"Loaded {len(truth_picks)} ground truth picks.")

    # 2. Run Pipeline
    start_time = time.time()

    # Run async pipeline
    local_picks = asyncio.run(run_pipeline(inputs))

    duration = time.time() - start_time
    print(f"Pipeline finished in {duration:.2f}s. Extracted {len(local_picks)} picks.")

    # 3. Compare
    tp, fp, fn, stats = compare_picks(local_picks, truth_picks)

    # 4. Report
    report = generate_report(tp, fp, fn, stats, duration)
    try:
        print("\n" + report)
    except UnicodeEncodeError:
        print("\n[Report suppressed due to console encoding error. See benchmark_report.md]")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved to: {REPORT_FILE}")


if __name__ == "__main__":
    main()
