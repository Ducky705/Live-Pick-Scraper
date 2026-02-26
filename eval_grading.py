import json
import logging
import os
import sys
from collections import defaultdict

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.grading.engine import GraderEngine
from src.score_fetcher import fetch_scores_for_date
from src.grading.parser import PickParser
from benchmark_golden_set import fuzzy_match

logging.basicConfig(level=logging.INFO, format='%(message)s')

def run_eval():
    parsing_file = r"benchmark\dataset\parsing_golden_set.json"
    results_file = "stepfun_results.json"

    with open(parsing_file, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)
        
    with open(results_file, 'r', encoding='utf-8') as f:
        extracted_picks = json.load(f)

    print("Fetching scores for 2026-02-14...")
    scores = fetch_scores_for_date("2026-02-14")
    grader = GraderEngine(scores)
    
    print("Grading...")
    # Grade extracted picks
    for p in extracted_picks:
        try:
            parsed = PickParser.parse(p.get("pick", ""), p.get("league", "Other"), p.get("date", "2026-02-14"))
            # ensure message_id
            if 'message_id' not in p and 'id' in p:
                p['message_id'] = p['id']
            graded = grader.grade(parsed)
            p["grade"] = graded.grade.value
        except Exception:
            p["grade"] = "ERROR"

    extracted_map = defaultdict(list)
    for p in extracted_picks:
        mid = str(p.get("message_id"))
        extracted_map[f"message_{mid}"].append(p)

    total_expected = 0
    total_found = 0
    total_correct = 0
    total_grades_expected = 0
    total_grades_correct = 0
    total_grades_miss = []

    for msg_key, expected_list in ground_truth.items():
        actual_list = extracted_map.get(msg_key, [])
        total_expected += len(expected_list)
        total_found += len(actual_list)
        
        used_actual_indices = set()
        
        for exp in expected_list:
            match_found = False
            for idx, act in enumerate(actual_list):
                if idx in used_actual_indices:
                    continue
                
                if fuzzy_match(exp, act):
                    match_found = True
                    used_actual_indices.add(idx)
                    total_correct += 1
                    
                    if 'grade' in exp:
                        total_grades_expected += 1
                        if exp['grade'] == act.get('grade'):
                            total_grades_correct += 1
                        else:
                            total_grades_miss.append({
                                'pick': exp.get('p'),
                                'expected_grade': exp['grade'],
                                'actual_grade': act.get('grade')
                            })
                    break

    precision = (total_correct / total_found * 100) if total_found > 0 else 0
    recall = (total_correct / total_expected * 100) if total_expected > 0 else 0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0

    print(f"Recall: {recall:.2f}%")
    print(f"Precision: {precision:.2f}%")
    print(f"F1: {f1:.2f}%")
    
    grading_accuracy = (total_grades_correct / total_grades_expected * 100) if total_grades_expected > 0 else 0
    print(f"Grading Accuracy: {grading_accuracy:.2f}% ({total_grades_correct}/{total_grades_expected})")

if __name__ == "__main__":
    run_eval()
