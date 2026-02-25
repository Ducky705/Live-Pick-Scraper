import json
import logging
from src.score_fetcher import fetch_scores_for_date
from src.grading.engine import GraderEngine
from src.grading.parser import PickParser

logging.basicConfig(level=logging.WARNING)

def test_matching():
    with open("benchmark/dataset/parsing_golden_set.json", "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    # All picks in golden set are from 2026-02-14
    scores = fetch_scores_for_date("2026-02-14")
    grader = GraderEngine(scores)

    total_picks = 0
    unresolved_picks = []

    for msg_id, picks in ground_truth.items():
        for pick_data in picks:
            total_picks += 1
            raw_text = pick_data.get("p", "")
            league = pick_data.get("lg", "Other")

            if not raw_text:
                continue

            parsed = PickParser.parse(raw_text, league, "2026-02-14")
            
            # Use the grader to see if it can resolve it
            # We don't necessarily care about the final grade WIN/LOSS, just if it finds the game.
            # But we can check if it returns PENDING with "Game not found"
            graded = grader.grade(parsed)
            
            if graded.grade.name == "PENDING" and "Game not found" in graded.details:
                unresolved_picks.append((raw_text, league, parsed.selection if parsed else "None"))
                print(f"FAILED MATCH: {raw_text} (League: {league}, Parsed Selection: {parsed.selection if parsed else 'None'})")

    print(f"\nTotal Picks Tested: {total_picks}")
    print(f"Total Unresolved: {len(unresolved_picks)}")
    
if __name__ == "__main__":
    test_matching()
