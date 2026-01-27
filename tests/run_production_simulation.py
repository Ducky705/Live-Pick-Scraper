import json
import os
import sys
import asyncio
import logging
import difflib
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.extraction_pipeline import ExtractionPipeline
from src.grader import grade_picks
from src.score_fetcher import fetch_scores_for_date
from src.models import BetPick
from src.grading.constants import LEAGUE_ALIASES_MAP

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ProductionSimulation")

GOLDEN_SET_PATH = os.path.join(os.path.dirname(__file__), "../new_golden_set.json")


def fuzzy_match(s1: str, s2: str) -> float:
    if not s1 or not s2:
        return 0.0
    return difflib.SequenceMatcher(None, str(s1).lower(), str(s2).lower()).ratio()


async def run_simulation():
    # Force ASCII for Windows console safety
    import sys

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    if not os.path.exists(GOLDEN_SET_PATH):
        logger.error("No golden set found!")
        return

    with open(GOLDEN_SET_PATH, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    logger.info(f"Loaded {len(test_cases)} test cases from Golden Set.")

    # Prepare messages
    messages = []
    for case in test_cases:
        messages.append(
            {
                "id": case["id"],
                "text": case["text"],
                "images": case.get("images", []),
                "date": case["date"],
                # Golden set usually has everything in 'text', but we can mock ocr fields
                "ocr_text": "",
                "ocr_texts": [],
            }
        )

    # Pick a target date from the first case (assuming all are roughly same day for batch test)
    # The golden set might have mixed dates. The pipeline usually processes one "target_date".
    # However, enrich_picks uses target_date to resolve "Today/Tomorrow".
    # We might need to group by date if they differ significantly.
    # checking new_golden_set.json content earlier, date was "2026-01-24 18:28 ET".
    # We strip time/timezone to get YYYY-MM-DD
    target_date = messages[0]["date"].split()[0]

    logger.info(f"Running ExtractionPipeline for target date: {target_date}")

    # RUN THE PIPELINE
    start_time = asyncio.get_event_loop().time()
    picks = ExtractionPipeline.run(messages, target_date)
    end_time = asyncio.get_event_loop().time()

    logger.info(
        f"Pipeline finished in {end_time - start_time:.2f}s. Extracted {len(picks)} picks."
    )

    # GRADE PICKS
    # We need to fetch scores. Since dates might vary in golden set, we should ideally fetch for all relevant dates.
    # But for now, let's assume the golden set is coherent or the date in picks is correct.
    # Picks have a 'date' field?
    # BetPick model has date.

    # We'll use the date from the picks if available, or fallback to target_date.
    # Fetch scores for the target date (and maybe surrounding days if needed).
    # actually grade_picks takes 'picks' and 'scores'.
    # scores is a list of GameScore objects.

    # Let's just fetch scores for the date in the first message for now.
    date_str = target_date.split()[0]

    logger.info(f"Fetching scores for {date_str}...")
    scores = fetch_scores_for_date(date_str)

    logger.info(f"Grading {len(picks)} picks...")
    graded_picks = grade_picks(picks, scores)

    # EVALUATE RESULTS
    total_picks_expected = 0
    total_picks_found = 0
    total_grades_matched = 0
    total_verified_grades = 0

    logger.info("Evaluating against Expected Results...")

    for case in test_cases:
        case_id = case["id"]
        expected_picks = case.get("expected_picks", [])
        total_picks_expected += len(expected_picks)

        # Find system picks for this case
        sys_picks = [
            p for p in graded_picks if str(p.get("message_id")) == str(case_id)
        ]

        found_indices = set()

        print(f"\n--- Case ID {case_id} ---")
        print(f"Expected: {len(expected_picks)} | Found: {len(sys_picks)}")

        for exp in expected_picks:
            best_match = None
            best_score = 0
            match_idx = -1

            exp_text = exp["pick"]

            for idx, sys_pick in enumerate(sys_picks):
                if idx in found_indices:
                    continue

                sys_text = sys_pick.get("pick", "")
                score = fuzzy_match(exp_text, sys_text)

                if score > best_score:
                    best_score = score
                    best_match = sys_pick
                    match_idx = idx

            if best_score > 0.6:
                found_indices.add(match_idx)
                total_picks_found += 1

                # Check Grade
                sys_grade = str(best_match.get("result", "Pending")).upper()
                verified_grade = str(exp.get("verified_grade", "PENDING")).upper()

                # Normalize
                if "WIN" in sys_grade:
                    sys_grade = "WIN"
                if "LOSS" in sys_grade:
                    sys_grade = "LOSS"
                if "PUSH" in sys_grade:
                    sys_grade = "PUSH"

                match_status = "[OK]"
                if verified_grade in ["WIN", "LOSS", "PUSH"]:
                    total_verified_grades += 1
                    if sys_grade == verified_grade:
                        total_grades_matched += 1
                    else:
                        match_status = "[GRADE MISMATCH]"

                sys_odds = best_match.get("odds")
                exp_odds = exp.get("odds")

                odds_status = ""
                if exp_odds is not None:
                    if str(sys_odds) == str(exp_odds):
                        odds_status = "[ODDS OK]"
                    else:
                        odds_status = f"[ODDS MISMATCH: {sys_odds} != {exp_odds}]"

                print(
                    f"  [MATCH {best_score:.2f}] {exp_text[:30]:<30} -> {best_match.get('pick', '')[:30]:<30} | {sys_grade} vs {verified_grade} {match_status} {odds_status}"
                )
            else:
                print(f"  [MISSING] {exp_text}")

        # Check for hallucinations (picks found but not expected)
        for idx, sys_pick in enumerate(sys_picks):
            if idx not in found_indices:
                print(
                    f"  [HALLUCINATION?] {sys_pick.get('pick', '')} (Type: {sys_pick.get('type')})"
                )

    # Final Stats

    recall = (
        (total_picks_found / total_picks_expected * 100) if total_picks_expected else 0
    )
    grade_acc = (
        (total_grades_matched / total_verified_grades * 100)
        if total_verified_grades
        else 0
    )

    print("\n" + "=" * 60)
    print("               SIMULATION RESULTS")
    print("=" * 60)
    print(f"Total Test Cases: {len(test_cases)}")
    print(f"Total Picks Expected: {total_picks_expected}")
    print(f"Total Picks Found:    {total_picks_found}")
    print(f"Recall Accuracy:      {recall:.2f}%")
    print("-" * 30)
    print(f"Verified Grades:      {total_verified_grades}")
    print(f"Grades Matched:       {total_grades_matched}")
    print(f"Grading Accuracy:     {grade_acc:.2f}%")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_simulation())
