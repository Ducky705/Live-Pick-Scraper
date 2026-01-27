import json
import os
import sys
import logging
from typing import List, Dict, Any

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.extraction_pipeline import ExtractionPipeline
from src.utils import clean_text_for_ai

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Verifier")


def normalize_string(s):
    if not s:
        return ""
    # Remove special chars but KEEP spaces for tokenization
    s = str(s).lower()
    # Replace common separators with space
    s = s.replace("/", " ").replace("-", " ").replace(":", " ").replace("|", " ")
    # Remove quotes and parentheses
    s = (
        s.replace("'", "")
        .replace('"', "")
        .replace("“", "")
        .replace("”", "")
        .replace("(", "")
        .replace(")", "")
    )

    # Remove common betting noise
    s = (
        s.replace(" vs ", " ")
        .replace(" versus ", " ")
        .replace(" @ ", " ")
        .replace(" games", "")
    )

    # Normalizations
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
    stop_words = {
        "the",
        "a",
        "an",
        "bet",
        "pick",
        "prediction",
        "of",
        "in",
        "ml",
        "moneyline",
    }
    exp_tokens -= stop_words
    act_tokens -= stop_words

    # Check for name overlap (Crucial)
    intersection = exp_tokens.intersection(act_tokens)

    # Calculate overlap ratio relative to expected length
    if not exp_tokens:
        return False
    ratio = len(intersection) / len(exp_tokens)

    pick_match = (
        (ratio >= 0.5)
        or (exp_pick_raw in act_pick_raw)
        or (act_pick_raw in exp_pick_raw)
    )

    # 2. League/Sport
    exp_league = normalize_string(expected.get("league"))
    act_league = normalize_string(actual.get("league"))

    # League equivalence map
    league_map = {
        "soccer": ["epl", "la liga", "serie a", "bundesliga", "ucl", "mls"],
        "ncaab": ["college basketball", "cbb"],
        "ncaaf": ["college football", "cfb"],
        "tennis": [
            "atp",
            "wta",
            "us open",
            "wimbledon",
            "french open",
            "australian open",
        ],
    }

    # Check map
    is_map_match = False
    if exp_league in league_map and act_league in league_map[exp_league]:
        is_map_match = True
    elif act_league in league_map and exp_league in league_map[act_league]:
        is_map_match = True

    league_match = (
        (exp_league in act_league)
        or (act_league in exp_league)
        or (not exp_league)
        or (act_league == "unknown")  # Allow unknown to pass validation if pick matches
        or (act_league == "other")
        or is_map_match
    )

    # 3. Odds
    odds_match = True
    if expected.get("odds") and actual.get("odds"):
        try:
            exp_odd = float(expected.get("odds"))
            act_odd = float(actual.get("odds"))
            # Allow slight difference (e.g. 1.90 vs 1.91 or -110 vs -115)
            # We allow a variance of 5 points for American odds or 0.05 for Decimal
            if abs(exp_odd) > 5.0:  # Likely American
                odds_match = (
                    abs(exp_odd - act_odd) <= 10.0
                )  # Allow -110 vs -115 difference
            else:
                odds_match = abs(exp_odd - act_odd) <= 0.05
        except:
            odds_match = str(expected.get("odds")) == str(actual.get("odds"))

    # Debug failure
    final_match = pick_match and league_match and odds_match

    # Special Handler for "PRA" / "Stats" format issues (e.g. "Over 44.5" vs "45+")
    if not final_match:
        # Check for PRA/Stats overlap
        if "pra" in exp_pick_raw and "pra" in act_pick_raw:
            # Check if numbers are compatible (X vs X-0.5)
            # Extract numbers
            import re

            exp_nums = re.findall(r"\d+\.?\d*", exp_pick_raw)
            act_nums = re.findall(r"\d+\.?\d*", act_pick_raw)
            if exp_nums and act_nums:
                e_val = float(exp_nums[0])
                a_val = float(act_nums[0])
                # Check for 0.5 diff (Over 44.5 == 45+)
                if abs(e_val - a_val) <= 0.6:
                    final_match = True

    return final_match


def run_verification():
    print("Loading Golden Set...")
    try:
        with open("new_golden_set.json", "r", encoding="utf-8") as f:
            golden_set = json.load(f)
    except FileNotFoundError:
        print("Error: new_golden_set.json not found.")
        return

    # Convert to pipeline messages
    messages = []
    for item in golden_set:
        msg = {
            "id": str(item["id"]),  # Ensure ID is string for pipeline consistency
            "date": item["date"],
            "text": item["text"],
            "images": item.get("images", []),
            "ocr_text": "",
            "ocr_texts": [],
            "source": item.get("source", "Telegram"),
        }
        messages.append(msg)

    print(f"Loaded {len(messages)} test cases.")

    # Run Pipeline
    target_date = "2026-01-24"  # Based on the file content seen
    print(f"Running Extraction Pipeline (Target Date: {target_date})...")

    # We allow the pipeline to run its course.
    # Note: This might make external API calls (OpenRouter/etc) depending on config.
    start_time = os.times().elapsed

    try:
        actual_picks = ExtractionPipeline.run(messages, target_date=target_date)
    except Exception as e:
        print(f"CRITICAL ERROR: Pipeline failed to run. {e}")
        import traceback

        traceback.print_exc()
        return

    end_time = os.times().elapsed
    print(
        f"Pipeline finished in {end_time - start_time:.2f}s. Extracted {len(actual_picks)} picks."
    )

    if actual_picks:
        print("DEBUG: First pick keys:", actual_picks[0].keys())
        print("DEBUG: First pick sample:", actual_picks[0])

    # Verification

    print("\n" + "=" * 50)
    print("VERIFICATION REPORT")
    print("=" * 50)

    total_expected = 0
    total_found = 0
    total_correct = 0

    # Group actual picks by message ID for easier lookup
    actual_picks_by_id = {}
    for p in actual_picks:
        mid = p.get("message_id")
        if mid not in actual_picks_by_id:
            actual_picks_by_id[mid] = []
        actual_picks_by_id[mid].append(p)

    for item in golden_set:
        mid = item["id"]
        expected_list = item.get("expected_picks", [])
        actual_list = actual_picks_by_id.get(str(mid), [])

        total_expected += len(expected_list)
        total_found += len(actual_list)

        print(f"\nMessage ID {mid}:")

        # Check for matches
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
                    print(
                        f"  [PASS] {exp['pick']} ({exp.get('odds')}) -> {act['pick']} ({act.get('odds')})"
                    )
                    break

            if not found:
                print(f"  [FAIL] MISSING: {exp['pick']} ({exp.get('odds')})")

        # Check for hallucinations (picks found but not expected)
        for i, act in enumerate(actual_list):
            if i not in matched_indices:
                print(f"  [WARN] UNEXPECTED: {act['pick']} ({act.get('odds')})")

    print("\n" + "=" * 50)
    print("SUMMARY")
    print(f"Total Expected Picks: {total_expected}")
    print(f"Total Found Picks:    {total_found}")
    print(f"Correctly Matched:    {total_correct}")

    accuracy = (total_correct / total_expected * 100) if total_expected > 0 else 0
    print(f"Accuracy: {accuracy:.2f}%")

    if accuracy >= 95:  # "Near PERFECT" threshold
        print("RESULT: PASSED (Ready for Production)")
    else:
        print("RESULT: FAILED (Needs Improvement)")


if __name__ == "__main__":
    run_verification()
