import json
import os
import sys

# Ensure src modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.grading.engine import GraderEngine
from src.grading.parser import PickParser
from src.score_fetcher import fetch_scores_for_date

def main():
    goldenset_file = 'benchmark/dataset/parsing_golden_set.json'
    with open(goldenset_file, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)

    # get all picks to find unique dates
    dates = set()
    for msg_id, msgs in ground_truth.items():
        for p in msgs:
            dates.add(p['dt'])
            
    print("Unique dates:", dates)

    dates_to_scores = {}
    for date in dates:
        print(f"Fetching scores for {date}...")
        dates_to_scores[date] = fetch_scores_for_date(date, force_refresh=False)
        print(f"Got {len(dates_to_scores[date])} scores for {date}")

    all_scores = []
    for scores in dates_to_scores.values():
        all_scores.extend(scores)

    engine = GraderEngine(all_scores)

    graded_truth = {}
    for msg_id, msgs in ground_truth.items():
        graded_msgs = []
        for p in msgs:
            bet_text = p.get('p', '')
            league = p.get('lg', 'Other')
            date = p.get('dt')
            try:
                parsed = PickParser.parse(bet_text, league, date)
                graded = engine.grade(parsed)
                p['grade'] = graded.grade.value
                p['grading_details'] = graded.details or graded.score_summary or ""
            except Exception as e:
                print(f"Error grading '{bet_text}': {e}")
                p['grade'] = "ERROR"
            graded_msgs.append(p)
        graded_truth[msg_id] = graded_msgs

    with open('benchmark/dataset/parsing_golden_set_graded.json', 'w', encoding='utf-8') as f:
        json.dump(graded_truth, f, indent=4)
        
    print("Wrote graded picks to benchmark/dataset/parsing_golden_set_graded.json")

    # analyze grades
    import collections
    grades = collections.Counter([p['grade'] for msgs in graded_truth.values() for p in msgs])
    print("Grades distribution:", grades)

if __name__ == "__main__":
    main()
