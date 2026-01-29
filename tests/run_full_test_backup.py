import asyncio
import difflib
import json
import logging
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.enrichment.engine import EnrichmentEngine  # Import the new engine
from src.grader import grade_picks
from src.models import BetPick
from src.openrouter_client import openrouter_completion
from src.prompt_builder import generate_ai_prompt
from src.prompts.decoder import normalize_response
from src.score_fetcher import fetch_scores_for_date

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FullRegression")

GOLDEN_SET_PATH = os.path.join(os.path.dirname(__file__), "../new_golden_set.json")


def fuzzy_match(s1: str, s2: str) -> float:
    if not s1 or not s2:
        return 0.0
    return difflib.SequenceMatcher(None, str(s1).lower(), str(s2).lower()).ratio()


async def run_test():
    if not os.path.exists(GOLDEN_SET_PATH):
        logger.error("No golden set found!")
        return

    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        test_cases = json.load(f)

    logger.info(f"Loaded {len(test_cases)} test cases.")

    total_picks_expected = 0
    total_picks_found = 0
    total_grades_matched = 0
    total_verified_grades = 0

    for i, case in enumerate(test_cases):
        logger.info(f"--- Case {i + 1} (ID: {case['id']}) ---")

        # 1. Simulate Pipeline (Text Processing)
        # We skip OCR/AutoProcessor for now as we are testing Text-to-Pick-to-Grade
        # Construct message object expected by prompt builder
        msg = {
            "id": case["id"],
            "text": case["text"],
            "images": case.get("images", []),  # Paths might be broken, but text is primary
            "date": case["date"],
        }

        # Generate Prompt
        prompt = generate_ai_prompt([msg])

        # Call AI (Production Model logic)
        # Using a cheaper model for test speed if possible, but ideally same as prod
        try:
            response = openrouter_completion(prompt, model="google/gemini-2.0-flash-exp:free")
            extracted_picks = normalize_response(response, expand=True)

            logger.info(f"  Extracted {len(extracted_picks)} picks.")

            # 1.5. ENRICHMENT STEP (The Fix)
            logger.info("  Running enrichment...")
            enricher = EnrichmentEngine()

            # Convert raw dicts to BetPick objects for enrichment
            # Note: normalize_response returns dicts, we need to wrap them
            bet_picks = []
            for p in extracted_picks:
                # Map extracted dict to BetPick model
                # Ensure fields match schema
                bp = BetPick(
                    message_id=msg["id"],
                    capper_name=p.get("capper_name") or p.get("c") or "Unknown",
                    league=p.get("league") or p.get("l") or "Unknown",
                    type=p.get("type") or p.get("t") or "Unknown",
                    pick=p.get("pick") or p.get("p") or "",
                    odds=p.get("odds") or p.get("o"),
                    units=p.get("units") or p.get("u") or 1.0,
                    date=msg["date"],
                )
                bet_picks.append(bp)

            enriched_picks = enricher.enrich_picks(bet_picks)

            # Convert back to dicts for grader (or update grader to accept objects)
            # The grader expects dicts usually, let's check
            extracted_picks_enriched = [
                {
                    "pick": p.pick,
                    "league": p.league,
                    "type": p.type,
                    "odds": p.odds,
                    "units": p.units,
                    "capper_name": p.capper_name,
                    "opponent": p.opponent,  # New field
                }
                for p in enriched_picks
            ]

            # 2. Grade the extracted picks (System Under Test)
            # We need to fetch scores for the message date to run the SYSTEM's grader
            date_str = case["date"].split()[0]
            scores = fetch_scores_for_date(date_str)

            graded_system_picks = grade_picks(extracted_picks_enriched, scores)

            # 3. Compare with Ground Truth
            expected_picks = case.get("expected_picks", [])
            total_picks_expected += len(expected_picks)

            found_indices = set()

            for exp in expected_picks:
                best_match = None
                best_score = 0
                match_idx = -1

                # Find matching extracted pick
                for idx, sys_pick in enumerate(graded_system_picks):
                    if idx in found_indices:
                        continue

                    sys_text = sys_pick.get("pick", sys_pick.get("p", ""))
                    score = fuzzy_match(exp["pick"], sys_text)

                    if score > best_score:
                        best_score = score
                        best_match = sys_pick
                        match_idx = idx

                if best_score > 0.6:
                    found_indices.add(match_idx)
                    total_picks_found += 1

                    # Compare Grades
                    sys_grade = best_match.get("result", "Pending").upper()
                    verified_grade = exp.get("verified_grade", "PENDING").upper()

                    # Normalize grades
                    if sys_grade == "WIN":
                        sys_grade = "WIN"
                    if sys_grade == "LOSS":
                        sys_grade = "LOSS"
                    if sys_grade == "PUSH":
                        sys_grade = "PUSH"

                    # Only compare if we have a definitive verified grade
                    if verified_grade in ["WIN", "LOSS", "PUSH"]:
                        total_verified_grades += 1
                        if sys_grade == verified_grade:
                            total_grades_matched += 1
                            logger.info(
                                f"  [MATCH] '{exp['pick']}' -> System: {sys_grade} | Verified: {verified_grade}"
                            )
                        else:
                            logger.error(
                                f"  [GRADE MISMATCH] '{exp['pick']}' -> System: {sys_grade} vs Verified: {verified_grade}"
                            )
                            logger.error(f"     System Proof: {best_match.get('score_summary')}")
                            logger.error(f"     Verified Proof: {exp.get('verification_proof')}")
                    else:
                        logger.info(f"  [Pick Found] '{exp['pick']}' (Grade: {sys_grade} - Verification unavailable)")
                else:
                    logger.warning(f"  [MISSING] Could not find pick: '{exp['pick']}'")

        except Exception as e:
            logger.error(f"  Pipeline Failed: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("               FINAL REGRESSION RESULTS")
    print("=" * 60)
    recall = (total_picks_found / total_picks_expected * 100) if total_picks_expected else 0
    grade_acc = (total_grades_matched / total_verified_grades * 100) if total_verified_grades else 0

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
    asyncio.run(run_test())
